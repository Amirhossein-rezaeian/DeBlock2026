# Blockchain-Anchored Data Continuity for Smart-City Digital Twins

**A dual-state verification framework — research code and experimental artifacts**

## Author

**Amirhossein Rezaeian**  
Engineering Education, Department of Engineering Science, College of Engineering, University of Tehran, Tehran, Iran  
Email: [develop.rezaeian@ut.ac.ir](mailto:develop.rezaeian@ut.ac.ir)  
ORCID: [0009-0009-4398-1703](https://orcid.org/0009-0009-4398-1703)  
Website: [https://autorz.ir/](https://autorz.ir/)

## Overview

This repository contains the source code and selected experimental artifacts associated with the research paper *“Blockchain-Anchored Data Continuity for Smart-City Digital Twins: A Dual-State Verification Framework.”*

The project implements an IoT-to-digital-twin data pipeline in which temperature readings are received from an ESP8266-based sensor node, stored in SQLite, fingerprinted with SHA-256, and associated with a hash-linked local ledger. A Streamlit dashboard presents the sensor records and ledger state alongside verification results.

The central verification idea is to assess two properties separately:

- **Ledger integrity:** whether the stored ledger structure and its hash links remain consistent with the verification rules.
- **Source-record coverage:** whether source records in the SQLite database have corresponding, uniquely resolved ledger references.

Separating these states makes it possible to identify a database in which the ledger is internally valid but one or more source records have not been anchored.

## Repository contents

```text
deblock2026_zenodo/
├── data/
│   └── urban_twin.db
├── evm/
│   ├── anchor_to_evm.py
│   └── contracts/
│       ├── contracts/
│       │   └── UrbanTwinRegistry.sol
│       ├── scripts/
│       │   └── deploy.js
│       ├── test/
│       │   └── UrbanTwinRegistry.js
│       ├── hardhat.config.js
│       └── package.json
├── multinode/
│   ├── dashboard_multinode.py
│   ├── network/
│   │   └── ledger_network.py
│   ├── run_demo.py
│   ├── tests/
│   │   └── test_network.py
│   └── verify_network.py
├── src/
│   ├── blockchain.py
│   ├── dashboard.py
│   ├── performance_test.py
│   ├── receiver.py
│   ├── tamper_scenarios.py
│   └── verify_blockchain.py
├── requirements-evm.txt
└── requirements.txt
```

### Main components

- `src/receiver.py` receives serial sensor messages and stores readings and their SHA-256 fingerprints in SQLite.
- `src/blockchain.py` contains the local hash-linked ledger operations.
- `src/verify_blockchain.py` checks source-to-ledger correspondence, record fingerprints, hash-chain consistency, unique references, and source-record coverage.
- `src/tamper_scenarios.py` runs controlled modifications against temporary database copies.
- `src/performance_test.py` measures local verification execution time over repeated runs.
- `src/dashboard.py` provides the Streamlit view of the digital-twin data and verification state.
- `evm/` contains the Solidity registry, deployment/test files, and Python integration used for local EVM anchoring.
- `multinode/` contains the experimental multi-replica ledger demonstration and its tests.
- `data/urban_twin.db` is the SQLite database snapshot included with this release.

## Experimental data snapshot

The included database snapshot corresponds to the research experiment and contains **481 source sensor records** and **482 ledger blocks** (one genesis block and 481 record-associated blocks). In the baseline snapshot, all 481 source records have unique ledger references, with no pending source records.

The database is included to support inspection and execution of the verification code against the released experimental snapshot. Running the receiver against new sensor input or modifying the database will change its contents and may change verification and performance results.

## Software requirements

The main Python components use the packages listed in `requirements.txt`:

- Python 3
- Streamlit
- pandas
- pyserial

The EVM integration additionally uses the package listed in `requirements-evm.txt`:

- web3.py

The Solidity project uses Node.js and the development dependencies declared in `evm/contracts/package.json` (Hardhat and Hardhat Toolbox).

## Reproducibility notes

The scripts are intended to be run from the project directory, with the relevant dependencies installed.

- The serial receiver requires an ESP8266 device connected to the host and a serial port configured for the device. The default port is `COM7`; it can be overridden with the `COM_PORT` environment variable. The default baud rate is `115200` and can be overridden with `BAUDRATE`.
- The dashboard and verification scripts use the included SQLite database at `data/urban_twin.db`.
- The performance script performs 20 local verification runs. Execution times depend on the host hardware, operating system, Python environment, database state, and background load; values should therefore be reported with the measurement environment.
- The controlled tampering scenarios operate on temporary copies of the database so that the released baseline database is not intentionally modified by those tests.
- The EVM scripts require a separately running local EVM JSON-RPC endpoint and a deployed contract. The endpoint and contract address are configured through environment variables (`EVM_RPC` and `CONTRACT_ADDRESS`).
- The multi-replica component is an experimental software demonstration. Its replicas run as processes/files on the same host; it should not be interpreted as evidence of geographically distributed consensus or production-grade blockchain decentralization.

## Scope and limitations

This release supports a hardware–software proof of concept for sensor-to-ledger data continuity and verification-aware digital-twin presentation. It does not demonstrate city-scale deployment, production-grade distributed consensus, independent external attestation, sensor identity authentication, sensor calibration or measurement accuracy, predictive urban simulation, or autonomous infrastructure control.

The local hash-linked ledger and the supplementary local EVM registry are distinct components. A successful local EVM anchoring test should not be interpreted as a public-chain deployment. Likewise, a valid hash does not establish that a sensor measurement is physically true; it detects inconsistencies relative to the stored records and verification procedure.

## Citation

If you use this software release or its experimental artifacts, please cite the software record:

> Rezaeian, A. (2026). *Blockchain-Anchored Data Continuity for Smart-City Digital Twins: A Dual-State Verification Framework* (Version 1.0.0). Zenodo. https://doi.org/10.5281/zenodo.24319719

**Software DOI:** [10.5281/zenodo.24319719](https://doi.org/10.5281/zenodo.24319719)

This DOI identifies the software record. It is distinct from any DOI that may be assigned to the associated conference paper. If you cite the paper itself, use the paper's own bibliographic record and DOI once available. Machine-readable citation metadata is provided in `CITATION.cff`.

## License

No open-source license is asserted by this README. Select and attach the license that you intend to grant when creating the Zenodo record. Until a license is specified, do not assume that the code is released under MIT, Apache-2.0, GPL, or another standard open-source license.

## Contact

For questions about the research implementation, please contact **Amirhossein Rezaeian** at [develop.rezaeian@ut.ac.ir](mailto:develop.rezaeian@ut.ac.ir).
