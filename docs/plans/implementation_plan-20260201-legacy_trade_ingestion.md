# Implementation Plan - Legacy Trade Ingestion

The goal is to ingest historical trade data (2020-2025) from legacy CSV files into the MongoDB `ibkr_trades` collection. We will adopt an ODS (Operational Data Store) pattern to store *all* available columns from the CSVs, ensuring no data loss from the different file versions (schema evolution).

## User Review Required
> [!NOTE]
> This process will upsert trades based on `TradeID` (or `TransactionID`). If a trade already exists, it will be updated with the merged data from the CSV. This is idempotent.

## Proposed Changes

### App Models
#### [MODIFY] [models.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models.py)
- Add `TradeRecord` model with `extra="allow"` to support dynamic CSV columns.

### Scripts
#### [NEW] [ingest_legacy_trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/ingest_legacy_trades.py)
- Standalone script to:
    1. Iterate through `ibkr-legacy-data/`.
    2. Parse each CSV using `csv.DictReader`.
    3. Normalize keys (remove spaces, handle different header names like `TradeID` vs `TransactionID`).
    4. Upsert into MongoDB `ibkr_trades`.

## Verification Plan

### Automated Tests
- **Run the Ingestion Script**:
    ```bash
    python ingest_legacy_trades.py
    ```
- **Verify Data in MongoDB**:
    - Check count of trades.
    - Check that a sample trade from 2024 has the extra columns (e.g., `Model`, `AssetClass`).
    - Check that a sample trade from 2021 has the standard columns.
    ```bash
    # Verification snippet (can be run in python shell or pytest)
    from pymongo import MongoClient
    from app.config import settings
    db = MongoClient(settings.MONGO_URI).get_default_database("stock_analysis")
    print(db.ibkr_trades.count_documents({}))
    print(db.ibkr_trades.find_one({"trade_id": "some_id_from_2024"}))
    ```
