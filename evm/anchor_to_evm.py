import json
import os
import sqlite3
from pathlib import Path

from web3 import Web3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_FILE = (
    PROJECT_ROOT
    / "evm"
    / "contracts"
    / "artifacts"
    / "contracts"
    / "UrbanTwinRegistry.sol"
    / "UrbanTwinRegistry.json"
)
DB_FILE = PROJECT_ROOT / "data" / "urban_twin.db"
RPC_URL = os.getenv("EVM_RPC", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ASSET_ID = os.getenv("ASSET_ID", "URBAN-001")


def main():
    if not ARTIFACT_FILE.exists():
        raise SystemExit("The contract artifact was not found.")

    if not CONTRACT_ADDRESS:
        raise SystemExit("CONTRACT_ADDRESS is not set.")

    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not web3.is_connected():
        raise SystemExit(f"Could not connect to the EVM endpoint: {RPC_URL}")

    artifact = json.loads(ARTIFACT_FILE.read_text(encoding="utf-8"))
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=artifact["abi"],
    )
    account = web3.eth.accounts[0]

    with sqlite3.connect(DB_FILE) as db:
        records = db.execute(
            """
            SELECT block_index, record_id, data_hash
            FROM blocks
            WHERE block_index > 0
            ORDER BY block_index
            """
        ).fetchall()

    submitted = 0
    verified = 0

    for block_index, record_id, digest in records:
        digest_bytes = bytes.fromhex(digest)
        current = contract.functions.getAnchor(
            ASSET_ID,
            int(record_id),
        ).call()

        if current[3]:
            if current[0] == digest_bytes and current[1] == int(block_index):
                verified += 1
                continue
            raise RuntimeError(
                f"An existing anchor does not match record {record_id}."
            )

        transaction = contract.functions.anchorRecord(
            ASSET_ID,
            int(record_id),
            digest_bytes,
            int(block_index),
        ).transact({"from": account})

        receipt = web3.eth.wait_for_transaction_receipt(transaction)
        if receipt.status != 1:
            raise RuntimeError(f"Anchor transaction failed for record {record_id}.")

        submitted += 1

        stored = contract.functions.getAnchor(
            ASSET_ID,
            int(record_id),
        ).call()

        if stored[3] and stored[0] == digest_bytes and stored[1] == int(block_index):
            verified += 1
        else:
            raise RuntimeError(f"Read-back verification failed for record {record_id}.")

    print("Records processed:", len(records))
    print("New anchors submitted:", submitted)
    print("Anchors verified:", verified)


if __name__ == "__main__":
    main()
