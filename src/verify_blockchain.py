import hashlib
import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT_ROOT / "data" / "urban_twin.db"


def make_block_hash(block):
    payload = {
        "block_index": block["block_index"],
        "db_id": block["db_id"],
        "record_id": block["record_id"],
        "temperature": block["temperature"],
        "record_time": block["record_time"],
        "data_hash": block["data_hash"],
        "previous_hash": block["previous_hash"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def make_sensor_hash(record_id, temperature, record_time):
    value = f"{int(record_id)}{float(temperature)}{record_time}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_database(db):
    source_rows = db.execute(
        """
        SELECT id, record_id, temperature, time, data_hash
        FROM temperature
        ORDER BY id
        """
    ).fetchall()

    block_rows = db.execute(
        """
        SELECT block_index, db_id, record_id, temperature,
               record_time, data_hash, previous_hash, block_hash
        FROM blocks
        ORDER BY block_index
        """
    ).fetchall()

    source_records = {row[0]: row for row in source_rows}
    source_ids = set(source_records)
    reference_counts = {}
    resolved_ids = set()
    problems = []
    previous_hash = "0"

    if not block_rows:
        problems.append("No blocks were found in the ledger.")

    for expected_index, row in enumerate(block_rows):
        (
            block_index,
            db_id,
            record_id,
            temperature,
            record_time,
            data_hash,
            stored_previous_hash,
            stored_block_hash,
        ) = row

        if block_index != expected_index:
            problems.append(
                f"Block numbering error: expected {expected_index}, found {block_index}."
            )

        block = {
            "block_index": block_index,
            "db_id": db_id,
            "record_id": record_id,
            "temperature": temperature,
            "record_time": record_time,
            "data_hash": data_hash,
            "previous_hash": stored_previous_hash,
        }

        if stored_previous_hash != previous_hash:
            problems.append(
                f"Previous-hash link is broken at block {block_index}."
            )

        if make_block_hash(block) != stored_block_hash:
            problems.append(
                f"Block content/hash mismatch at block {block_index}."
            )

        if block_index == 0:
            valid_genesis = (
                db_id is None
                and record_id == 0
                and temperature is None
                and record_time == "GENESIS"
                and data_hash == "GENESIS"
                and stored_previous_hash == "0"
            )
            if not valid_genesis:
                problems.append("Genesis block fields are not correct.")
        else:
            if db_id is None:
                problems.append(
                    f"Block {block_index} has no source database ID."
                )
            else:
                reference_counts[db_id] = reference_counts.get(db_id, 0) + 1
                source_row = source_records.get(db_id)

                if source_row is None:
                    problems.append(
                        f"Source record {db_id} for block {block_index} was not found."
                    )
                else:
                    resolved_ids.add(db_id)
                    (
                        _,
                        source_record_id,
                        source_temperature,
                        source_time,
                        source_hash,
                    ) = source_row

                    fields_match = (
                        source_record_id == record_id
                        and source_temperature == temperature
                        and str(source_time) == str(record_time)
                        and str(source_hash) == str(data_hash)
                    )

                    if not fields_match:
                        problems.append(
                            f"Block {block_index} does not match source record {db_id}."
                        )

        previous_hash = stored_block_hash

    for db_id, count in reference_counts.items():
        if count > 1:
            problems.append(
                f"Source record {db_id} is referenced by more than one block."
            )

    for db_id in resolved_ids:
        source_row = source_records[db_id]
        _, record_id, temperature, record_time, stored_digest = source_row
        expected_digest = make_sensor_hash(record_id, temperature, record_time)
        if expected_digest != stored_digest:
            problems.append(
                f"Sensor-data hash mismatch for source record {db_id}."
            )

    uniquely_referenced = {
        db_id
        for db_id, count in reference_counts.items()
        if count == 1 and db_id in source_ids
    }
    pending_ids = source_ids - uniquely_referenced

    return {
        "integrity": "INVALID" if problems else "VALID",
        "coverage": "COMPLETE" if not pending_ids else "INCOMPLETE",
        "source_records": len(source_rows),
        "total_blocks": len(block_rows),
        "anchored_records": len(uniquely_referenced),
        "pending_records": len(pending_ids),
        "problems": problems,
    }


def main():
    if not DB_FILE.exists():
        raise SystemExit(f"Database file not found: {DB_FILE}")

    try:
        with sqlite3.connect(DB_FILE, timeout=10) as db:
            db.execute("PRAGMA busy_timeout = 10000")
            result = verify_database(db)
    except sqlite3.Error as error:
        raise SystemExit(f"Database error: {error}") from error

    print("Smart-City Digital-Twin Ledger Verification")
    print("=" * 48)
    print("Source records:", result["source_records"])
    print("Total blocks:", result["total_blocks"])
    print("Uniquely referenced records:", result["anchored_records"])
    print("Pending records:", result["pending_records"])
    print("Integrity:", result["integrity"])
    print("Coverage:", result["coverage"])

    if result["problems"]:
        for problem in result["problems"]:
            print("Problem:", problem)

    if result["integrity"] == "INVALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
