import hashlib
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from blockchain import make_block_hash
from verify_blockchain import DB_FILE, make_sensor_hash, verify_database


def rehash_ledger(db):
    rows = db.execute(
        """
        SELECT block_index, db_id, record_id, temperature,
               record_time, data_hash
        FROM blocks
        ORDER BY block_index
        """
    ).fetchall()

    previous_hash = "0"

    for row in rows:
        block_index, db_id, record_id, temperature, record_time, data_hash = row
        block = {
            "block_index": block_index,
            "db_id": db_id,
            "record_id": record_id,
            "temperature": temperature,
            "record_time": record_time,
            "data_hash": data_hash,
            "previous_hash": previous_hash,
        }
        block_hash = make_block_hash(block)

        db.execute(
            """
            UPDATE blocks
            SET previous_hash = ?, block_hash = ?
            WHERE block_index = ?
            """,
            (previous_hash, block_hash, block_index),
        )
        previous_hash = block_hash

    db.commit()


def run_case(name, modify):
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db = Path(temp_dir) / "scenario.db"
        shutil.copy2(DB_FILE, test_db)

        with sqlite3.connect(test_db) as db:
            modify(db)
            result = verify_database(db)

        return name, result


def change_measurement(db):
    db.execute(
        "UPDATE blocks SET temperature = 99.0 WHERE block_index = 1"
    )


def change_sensor_digest(db):
    row = db.execute(
        "SELECT db_id FROM blocks WHERE block_index = 1"
    ).fetchone()
    db_id = row[0]
    altered_digest = "TAMPERED_SENSOR_HASH"

    db.execute(
        "UPDATE temperature SET data_hash = ? WHERE id = ?",
        (altered_digest, db_id),
    )
    db.execute(
        "UPDATE blocks SET data_hash = ? WHERE block_index = 1",
        (altered_digest,),
    )
    rehash_ledger(db)


def change_block_hash(db):
    db.execute(
        "UPDATE blocks SET block_hash = ? WHERE block_index = 1",
        ("INVALID_BLOCK_HASH",),
    )


def change_previous_hash(db):
    db.execute(
        "UPDATE blocks SET previous_hash = ? WHERE block_index = 2",
        ("BROKEN_PREVIOUS_HASH",),
    )


def delete_source_record(db):
    row = db.execute(
        "SELECT db_id FROM blocks WHERE block_index = 1"
    ).fetchone()
    db.execute("DELETE FROM temperature WHERE id = ?", (row[0],))


def add_pending_record(db):
    record_id = 9999
    temperature = 27.5
    timestamp = datetime.now().isoformat(timespec="seconds")
    digest = make_sensor_hash(record_id, temperature, timestamp)

    db.execute(
        """
        INSERT INTO temperature (record_id, temperature, time, data_hash)
        VALUES (?, ?, ?, ?)
        """,
        (record_id, temperature, timestamp, digest),
    )


def main():
    scenarios = (
        ("Scenario 1 - measurement alteration", change_measurement),
        ("Scenario 2 - source digest alteration", change_sensor_digest),
        ("Scenario 3 - block hash alteration", change_block_hash),
        ("Scenario 4 - previous-hash alteration", change_previous_hash),
        ("Scenario 5 - source-row deletion", delete_source_record),
        ("Scenario 6 - pending source record", add_pending_record),
    )

    for name, modify in scenarios:
        scenario_name, result = run_case(name, modify)
        print(scenario_name)
        print("Integrity:", result["integrity"])
        print("Coverage:", result["coverage"])
        print("Anchored:", result["anchored_records"])
        print("Pending:", result["pending_records"])

        for problem in result["problems"]:
            print("Detected:", problem)

        print("-" * 54)


if __name__ == "__main__":
    main()
