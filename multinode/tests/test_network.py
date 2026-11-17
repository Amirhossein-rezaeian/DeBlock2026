import hashlib
import shutil
import sqlite3
import tempfile
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "multinode"))

from network import ledger_network as net


SOURCE_DB = PROJECT_ROOT / "data" / "urban_twin.db"


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_nodes_dir = net.NODES_DIR
        net.NODES_DIR = self.temp_dir / "nodes"
        self.source_db = self.temp_dir / "source.db"
        shutil.copy2(SOURCE_DB, self.source_db)
        net.initialize_nodes(self.source_db, reset=True)

    def tearDown(self):
        net.NODES_DIR = self.original_nodes_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def add_record(self, record_id=777001):
        timestamp = "2026-11-17T12:00:00+00:00"
        temperature = 24.5
        raw_value = f"{record_id}{float(temperature)}{timestamp}"
        digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

        with sqlite3.connect(self.source_db) as db:
            db.execute(
                """
                INSERT INTO temperature
                    (record_id, temperature, time, data_hash)
                VALUES (?, ?, ?, ?)
                """,
                (record_id, temperature, timestamp, digest),
            )

    def test_three_ledgers_start_valid(self):
        states = net.status()
        self.assertEqual(len(states), 3)
        self.assertTrue(all(item["valid"] for item in states))
        self.assertEqual(
            len({str(net.NODES_DIR / f"{name}.db") for name in net.NODE_NAMES}),
            3,
        )

    def test_majority_accepts_record(self):
        self.add_record()
        result = net.append_pending(self.source_db)

        self.assertTrue(result[0]["accepted"])
        self.assertEqual(result[0]["yes_votes"], 3)
        self.assertTrue(all(item["valid"] for item in net.status()))
        self.assertEqual(len({item["blocks"] for item in net.status()}), 1)

    def test_one_offline_node_still_reaches_quorum(self):
        self.add_record()
        result = net.append_pending(
            self.source_db,
            offline=("node_3",),
        )

        self.assertTrue(result[0]["accepted"])
        self.assertEqual(result[0]["yes_votes"], 2)

        valid, message = net.sync_node_from_source("node_3", self.source_db)
        self.assertTrue(valid, message)
        self.assertEqual(len({item["blocks"] for item in net.status()}), 1)

    def test_two_offline_nodes_do_not_reach_quorum(self):
        self.add_record()
        result = net.append_pending(
            self.source_db,
            offline=("node_2", "node_3"),
        )

        self.assertFalse(result[0]["accepted"])
        self.assertEqual(result[0]["yes_votes"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
