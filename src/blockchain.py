import hashlib
import json
import sqlite3
from pathlib import Path

from verify_blockchain import DB_FILE, make_sensor_hash, verify_database


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


def create_tables(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS blocks (
            block_index INTEGER PRIMARY KEY,
            db_id INTEGER UNIQUE,
            record_id INTEGER,
            temperature REAL,
            record_time TEXT,
            data_hash TEXT,
            previous_hash TEXT,
            block_hash TEXT NOT NULL
        )
        """
    )
    db.commit()


def create_genesis_block(db):
    count = db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
    if count:
        return

    block = {
        "block_index": 0,
        "db_id": None,
        "record_id": 0,
        "temperature": None,
        "record_time": "GENESIS",
        "data_hash": "GENESIS",
        "previous_hash": "0",
    }
    block_hash = make_block_hash(block)

    db.execute(
        """
        INSERT INTO blocks
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            0,
            None,
            0,
            None,
            "GENESIS",
            "GENESIS",
            "0",
            block_hash,
        ),
    )
    db.commit()


def append_pending_records(db):
    result = verify_database(db)
    if result["integrity"] != "VALID":
        raise RuntimeError("The existing ledger failed verification.")

    pending_rows = db.execute(
        """
        SELECT t.id, t.record_id, t.temperature, t.time, t.data_hash
        FROM temperature AS t
        LEFT JOIN blocks AS b ON b.db_id = t.id
        WHERE b.db_id IS NULL
        ORDER BY t.id
        """
    ).fetchall()

    for db_id, record_id, temperature, record_time, data_hash in pending_rows:
        expected_digest = make_sensor_hash(record_id, temperature, record_time)
        if expected_digest != data_hash:
            raise ValueError(f"Source record {db_id} has an invalid sensor hash.")

        previous = db.execute(
            """
            SELECT block_index, block_hash
            FROM blocks
            ORDER BY block_index DESC
            LIMIT 1
            """
        ).fetchone()

        block = {
            "block_index": previous[0] + 1,
            "db_id": db_id,
            "record_id": record_id,
            "temperature": temperature,
            "record_time": record_time,
            "data_hash": data_hash,
            "previous_hash": previous[1],
        }

        block_hash = make_block_hash(block)
        db.execute(
            """
            INSERT INTO blocks
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block["block_index"],
                db_id,
                record_id,
                temperature,
                record_time,
                data_hash,
                block["previous_hash"],
                block_hash,
            ),
        )

    db.commit()
    return len(pending_rows)


def main():
    if not DB_FILE.exists():
        raise SystemExit(f"Database file not found: {DB_FILE}")

    with sqlite3.connect(DB_FILE, timeout=10) as db:
        db.execute("PRAGMA busy_timeout = 10000")
        create_tables(db)
        create_genesis_block(db)
        added = append_pending_records(db)
        result = verify_database(db)

    print("New blocks:", added)
    print("Source records:", result["source_records"])
    print("Total blocks:", result["total_blocks"])
    print("Integrity:", result["integrity"])
    print("Coverage:", result["coverage"])

    if result["problems"]:
        for problem in result["problems"]:
            print("Problem:", problem)

    if result["integrity"] != "VALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
