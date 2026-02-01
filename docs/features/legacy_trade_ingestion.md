# Legacy Trade Ingestion Feature

## Overview
This feature enables the standard ingestion of historical IBKR trade data (CSV export format) into the system's `ibkr_trades` MongoDB collection. It is designed to handle schema evolution across different years (2020-2025) and ensures data idempotency.

## Requirements

- **Data Sources**: Legacy CSV files in `ibkr-legacy-data/`.
- **Format Variations**: Must handle varying headers (e.g., `TradeID`, `TransactionID`, `IBTransactionID`).
- **Data Integrity**: Store ALL columns present in the CSV (ODS pattern), even if not strictly defined in the schema.
- **Idempotency**: Re-running ingestion must not create duplicates; it should update existing records based on unique IDs.
- **Mapping**: Internal data model uses snake_case (`trade_id`), mapped from CSV CamelCase.

## Implementation Details

### Components
1.  **Script**: `ingest_legacy_trades.py`
    - Scans `ibkr-legacy-data/*.csv`.
    - Normalizes row keys (strips whitespace, standardizes ID field).
    - Upserts to MongoDB.
2.  **Model**: `app.models.TradeRecord`
    - Defines core fields (`trade_id`, `symbol`, `quantity`, `date_time`).
    - Uses `extra="allow"` to capture all other CSV columns.

### Usage
Run the script manually to ingest or update data:
```bash
python ingest_legacy_trades.py
```

### Testing
Unit tests are located in `tests/test_ingest_legacy_trades.py`.
Run with:
```bash
pytest tests/test_ingest_legacy_trades.py
```

## Future Considerations
- Integration into the main scheduler/pipeline if trade ingestion becomes a regular automated task (currently more of a one-off or ad-hoc backfill).
