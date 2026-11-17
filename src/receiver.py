import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import serial


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT_ROOT / "data" / "urban_twin.db"
PORT = os.getenv("COM_PORT", "COM7")
BAUDRATE = int(os.getenv("BAUDRATE", "115200"))


def create_source_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS temperature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            temperature REAL,
            time TEXT,
            data_hash TEXT
        )
        """
    )
    db.commit()


def make_sensor_hash(record_id, temperature, timestamp):
    value = f"{record_id}{float(temperature)}{timestamp}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    db = sqlite3.connect(DB_FILE, timeout=15)
    db.execute("PRAGMA busy_timeout = 15000")
    create_source_table(db)

    board = None

    try:
        board = serial.Serial(PORT, BAUDRATE, timeout=2)
        print(f"Connected to {PORT}")
        print(f"Database: {DB_FILE}")

        while True:
            line = board.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            if "record_id" not in payload or "temperature_c" not in payload:
                continue

            record_id = int(payload["record_id"])
            temperature = float(payload["temperature_c"])
            timestamp = datetime.now().isoformat(timespec="seconds")
            digest = make_sensor_hash(record_id, temperature, timestamp)

            db.execute(
                """
                INSERT INTO temperature
                    (record_id, temperature, time, data_hash)
                VALUES (?, ?, ?, ?)
                """,
                (record_id, temperature, timestamp, digest),
            )
            db.commit()

            print(
                f"Record {record_id} | {temperature:.1f} C | "
                f"{timestamp} | {digest[:16]}"
            )

    except KeyboardInterrupt:
        print("Data collection stopped.")
    finally:
        if board is not None:
            board.close()
        db.close()


if __name__ == "__main__":
    main()
