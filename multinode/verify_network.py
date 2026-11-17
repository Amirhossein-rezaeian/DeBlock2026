import sys

from network.ledger_network import NODES_DIR, NODE_NAMES, connect, verify_ledger


def main():
    all_valid = True

    for name in NODE_NAMES:
        node_path = NODES_DIR / f"{name}.db"

        if not node_path.exists():
            print(f"{name}: NOT INITIALIZED")
            all_valid = False
            continue

        db = connect(node_path)
        valid, message = verify_ledger(db)
        block_count = db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        db.close()

        print(
            f"{name}: {'VALID' if valid else 'INVALID'} | "
            f"blocks={block_count} | {message}"
        )
        all_valid = all_valid and valid

    print("NETWORK LEDGER STATUS:", "VALID" if all_valid else "INVALID")

    if not all_valid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
