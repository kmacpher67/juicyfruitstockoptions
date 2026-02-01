# Walkthrough: Legacy Trade Ingestion

## Overview
We have successfully implemented a robust ingestion process for legacy IBKR trade CSVs (2020-2025). The solution handles schema variations, ensures idempotency, and preserves all original data fields.

## Key Components

### 1. Ingestion Script (`ingest_legacy_trades.py`)
This script parses CSV files, normalizes headers, and upserts data into MongoDB.

**Features:**
- **Schema Normalization**: Maps `TransactionID` / `IBTransactionID` to a unified `TradeID`.
- **ODS Pattern**: Stores *all* columns found in the CSV, even those not explicitly defined in the core model.
- **Idempotency**: Uses `update_one(upsert=True)` keyed by `trade_id` to prevent duplicates on re-runs.
- **Safety**: Skips rows without valid IDs (e.g., subtotals).

### 2. Data Model (`app/models.py`)
The `TradeRecord` model has been updated to support the ingestion:
- **Snake Case Internal Fields**: `trade_id`, `symbol`, `quantity`.
- **Aliases**: parsing from CamelCase CSV headers.
- **Extra Fields**: `model_config = {"extra": "allow"}`.

### 3. Unit Tests (`tests/test_ingest_legacy_trades.py`)
Comprehensive tests covering:
- **Normalization**: Verifying correct ID extraction and numeric parsing.
- **Legacy Formats**: Ensuring old files with `TransactionID` work.
- **File Ingestion**: Mocked testing of the full file processing loop, including file seeking/reading and DB upserts.
- **Skipping**: Verifying that subtotal lines are ignored.

## Verification Results

### Test Execution
All unit tests passed successfully.

```bash
$ pytest tests/test_ingest_legacy_trades.py 
============================= test session starts ==============================
collected 5 items                                                              

tests/test_ingest_legacy_trades.py .....                                 [100%]

============================== 5 passed in 0.26s ===============================
```

### Manual Verification (Summary)
- **Duplicate Removal**: A cleanup script was run to remove old CamelCase records.
- **Record Count**: Verified that records are correctly stored with `trade_id`.
