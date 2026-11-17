import hashlib
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from network import ledger_network as net


def main():
    with tempfile.TemporaryDirectory() as temporary_directory:
        work_dir = Path(temporary_directory)
        demo_db = work_dir / "urban_twin_demo.db"
        shutil.copy2(net.DEFAULT_SOURCE, demo_db)

        record_id = 900001
        temperature = 26.7
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        digest = net.sensor_hash(record_id, temperature, timestamp)

        with sqlite3.connect(demo_db) as db:
            db.execute(
                """
                INSERT INTO temperature
                    (record_id, temperature, time, data_hash)
                VALUES (?, ?, ?, ?)
                """,
                (record_id, temperature, timestamp, digest),
            )

        net.NODES_DIR = work_dir / "nodes"
        net.initialize_nodes(demo_db, reset=True)

        print("Before majority vote:")
        for item in net.status():
            print(item)

        results = net.append_pending(demo_db)

        print()
        print("Majority-vote result:")
        for item in results:
            print(item)

        print()
        print("After majority vote:")
        for item in net.status():
            print(item)


if __name__ == "__main__":
    main()
