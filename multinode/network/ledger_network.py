import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = COMPONENT_ROOT.parent
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "urban_twin.db"
NODES_DIR = COMPONENT_ROOT / "nodes"
NODE_NAMES = ("node_1", "node_2", "node_3")
QUORUM = 2


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sensor_hash(record_id, temperature, record_time):
    value = f"{int(record_id)}{float(temperature)}{record_time}"
    return sha256_text(value)


def block_payload(row):
    return {
        "block_index": int(row[0]),
        "db_id": row[1],
        "record_id": int(row[2]),
        "temperature": row[3],
        "record_time": row[4],
        "data_hash": row[5],
        "previous_hash": row[6],
    }


def block_hash(payload):
    return sha256_text(canonical_json(payload))


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS blocks (
            block_index INTEGER PRIMARY KEY,
            db_id INTEGER UNIQUE,
            record_id INTEGER,
            temperature REAL,
            record_time TEXT,
            data_hash TEXT,
            previous_hash TEXT NOT NULL,
            block_hash TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS node_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    db.commit()
    return db


def rows(db):
    return db.execute(
        """
        SELECT block_index, db_id, record_id, temperature,
               record_time, data_hash, previous_hash, block_hash
        FROM blocks
        ORDER BY block_index
        """
    ).fetchall()


def verify_ledger(db):
    ledger_rows = rows(db)
    if not ledger_rows:
        return False, "empty ledger"

    previous_hash = "0"
    seen_ids = set()

    for expected_index, row in enumerate(ledger_rows):
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
            return False, f"index gap at block {block_index}"

        if stored_previous_hash != previous_hash:
            return False, f"previous-hash mismatch at block {block_index}"

        if block_hash(block_payload(row)) != stored_block_hash:
            return False, f"block hash mismatch at block {block_index}"

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
                return False, "invalid genesis block"
        else:
            if db_id is None or db_id in seen_ids:
                return False, f"missing or duplicate source ID at block {block_index}"
            seen_ids.add(db_id)

        previous_hash = stored_block_hash

    return True, "valid"


def genesis_tuple():
    payload = {
        "block_index": 0,
        "db_id": None,
        "record_id": 0,
        "temperature": None,
        "record_time": "GENESIS",
        "data_hash": "GENESIS",
        "previous_hash": "0",
    }
    return (
        0,
        None,
        0,
        None,
        "GENESIS",
        "GENESIS",
        "0",
        block_hash(payload),
    )


def initialize_nodes(source_db_path=DEFAULT_SOURCE, reset=False):
    source_db_path = Path(source_db_path)
    if not source_db_path.exists():
        raise FileNotFoundError(source_db_path)

    with sqlite3.connect(source_db_path) as source:
        source_blocks = source.execute(
            """
            SELECT block_index, db_id, record_id, temperature,
                   record_time, data_hash, previous_hash, block_hash
            FROM blocks
            ORDER BY block_index
            """
        ).fetchall()

    if not source_blocks:
        source_blocks = [genesis_tuple()]

    for name in NODE_NAMES:
        node_path = NODES_DIR / f"{name}.db"
        if reset and node_path.exists():
            node_path.unlink()

        node = connect(node_path)
        count = node.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]

        if count == 0:
            node.executemany(
                "INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                source_blocks,
            )
            node.execute(
                "INSERT OR REPLACE INTO node_meta VALUES (?, ?)",
                ("node_name", name),
            )
            node.commit()

        valid, message = verify_ledger(node)
        node.close()

        if not valid:
            raise RuntimeError(f"{name} failed initial verification: {message}")

    return status()


def status():
    results = []

    for name in NODE_NAMES:
        node_path = NODES_DIR / f"{name}.db"

        if not node_path.exists():
            results.append(
                {
                    "node": name,
                    "available": False,
                    "valid": False,
                    "blocks": 0,
                    "message": "not initialized",
                }
            )
            continue

        db = connect(node_path)
        valid, message = verify_ledger(db)
        block_count = db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        db.close()

        results.append(
            {
                "node": name,
                "available": True,
                "valid": valid,
                "blocks": block_count,
                "message": message,
            }
        )

    return results


def source_unanchored_records(source_db_path):
    with sqlite3.connect(source_db_path) as source:
        source.row_factory = sqlite3.Row
        try:
            records = source.execute(
                """
                SELECT t.id, t.record_id, t.temperature, t.time, t.data_hash
                FROM temperature AS t
                LEFT JOIN blocks AS b ON b.db_id = t.id
                WHERE b.db_id IS NULL
                ORDER BY t.id
                """
            ).fetchall()
        except sqlite3.Error as error:
            raise RuntimeError(
                f"Source database schema or blocks table is unavailable: {error}"
            ) from error

    return records


def make_candidate(source_record, previous_row):
    last_index, last_hash = previous_row
    db_id = int(source_record["id"])
    record_id = int(source_record["record_id"])
    temperature = float(source_record["temperature"])
    timestamp = str(source_record["time"])
    digest = str(source_record["data_hash"])

    if sensor_hash(record_id, temperature, timestamp) != digest:
        raise ValueError(f"Source record {db_id} has an invalid sensor hash.")

    payload = {
        "block_index": last_index + 1,
        "db_id": db_id,
        "record_id": record_id,
        "temperature": temperature,
        "record_time": timestamp,
        "data_hash": digest,
        "previous_hash": last_hash,
    }

    return (
        payload["block_index"],
        payload["db_id"],
        payload["record_id"],
        payload["temperature"],
        payload["record_time"],
        payload["data_hash"],
        payload["previous_hash"],
        block_hash(payload),
    )


def node_vote(name, candidate, offline=()):
    if name in offline:
        return False, "offline"

    db = connect(NODES_DIR / f"{name}.db")
    valid, message = verify_ledger(db)

    if not valid:
        db.close()
        return False, f"local ledger invalid: {message}"

    last = db.execute(
        """
        SELECT block_index, block_hash
        FROM blocks
        ORDER BY block_index DESC
        LIMIT 1
        """
    ).fetchone()
    db.close()

    index, _, record_id, temperature, timestamp, digest, previous_hash, stored_hash = candidate
    approved = (
        index == last[0] + 1
        and previous_hash == last[1]
        and sensor_hash(record_id, temperature, timestamp) == digest
        and block_hash(block_payload(candidate)) == stored_hash
    )

    return approved, "approve" if approved else "reject"


def append_to_node(name, candidate):
    db = connect(NODES_DIR / f"{name}.db")
    db.execute(
        "INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        candidate,
    )
    db.commit()
    valid, message = verify_ledger(db)
    db.close()

    if not valid:
        raise RuntimeError(f"Post-commit validation failed for {name}: {message}")


def sync_node_from_source(name, source_db_path=DEFAULT_SOURCE):
    with sqlite3.connect(source_db_path) as source:
        canonical = source.execute(
            """
            SELECT block_index, db_id, record_id, temperature,
                   record_time, data_hash, previous_hash, block_hash
            FROM blocks
            ORDER BY block_index
            """
        ).fetchall()

    node = connect(NODES_DIR / f"{name}.db")
    local = rows(node)

    if len(local) > len(canonical) or local != canonical[:len(local)]:
        node.close()
        return False, "ledger diverged; refusing automatic overwrite"

    if len(local) < len(canonical):
        node.executemany(
            "INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            canonical[len(local):],
        )
        node.commit()

    valid, message = verify_ledger(node)
    node.close()
    return valid, message


def append_pending(source_db_path=DEFAULT_SOURCE, offline=()):
    pending_records = source_unanchored_records(source_db_path)
    outcomes = []

    for record in pending_records:
        available_tips = []

        for name in NODE_NAMES:
            if name in offline:
                continue

            db = connect(NODES_DIR / f"{name}.db")
            valid, _ = verify_ledger(db)
            last = None

            if valid:
                last = db.execute(
                    """
                    SELECT block_index, block_hash
                    FROM blocks
                    ORDER BY block_index DESC
                    LIMIT 1
                    """
                ).fetchone()

            db.close()

            if last is not None:
                available_tips.append((last[0], last[1]))

        if not available_tips:
            outcomes.append(
                {
                    "record_id": record["id"],
                    "accepted": False,
                    "reason": "no online valid node",
                }
            )
            continue

        if len(set(available_tips)) != 1:
            outcomes.append(
                {
                    "record_id": record["id"],
                    "accepted": False,
                    "reason": "node ledgers diverged; manual reconciliation required",
                }
            )
            continue

        candidate = make_candidate(record, available_tips[0])
        votes = {}

        for name in NODE_NAMES:
            approved, reason = node_vote(name, candidate, offline=offline)
            votes[name] = {
                "vote": "YES" if approved else "NO",
                "reason": reason,
            }

        yes_votes = sum(vote["vote"] == "YES" for vote in votes.values())
        accepted = yes_votes >= QUORUM

        if accepted:
            for name in NODE_NAMES:
                if name not in offline:
                    append_to_node(name, candidate)

            with sqlite3.connect(source_db_path) as archive:
                archive.execute(
                    "INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    candidate,
                )

        outcomes.append(
            {
                "record_id": record["id"],
                "accepted": accepted,
                "yes_votes": yes_votes,
                "required": QUORUM,
                "votes": votes,
                "block_index": candidate[0] if accepted else None,
            }
        )

    return outcomes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--offline", default="")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()

    offline_nodes = tuple(
        name.strip()
        for name in args.offline.split(",")
        if name.strip()
    )

    if args.reset or not all(
        (NODES_DIR / f"{name}.db").exists() for name in NODE_NAMES
    ):
        initialize_nodes(args.source, reset=args.reset)

    if args.sync:
        for name in NODE_NAMES:
            if name not in offline_nodes:
                print("SYNC", name, sync_node_from_source(name, args.source))

    print("Node status:")
    for item in status():
        print(item)

    if args.append:
        print()
        print("Majority-vote results:")
        for item in append_pending(args.source, offline_nodes):
            print(json.dumps(item, ensure_ascii=False))

    print()
    print("Final node status:")
    for item in status():
        print(item)


if __name__ == "__main__":
    main()
