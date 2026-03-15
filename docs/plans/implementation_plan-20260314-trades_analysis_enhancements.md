# Trades Backend Enhancements and Data Cleanup

This plan addresses the requirement to add debug logging to the trades backend and investigate/fix the missing account data in the trades view.

## User Review Required

> [!IMPORTANT]
> I have identified that some trades in the `ibkr_trades` collection are missing `AccountId` fields. I plan to identify why this is happening (likely during ingestion) and potentially clean up or fix these records.

## Proposed Changes

### Backend API and Models

#### [MODIFY] [trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/trades.py)
- Add `DEBUG` level logging for all incoming trade and analysis requests.
- Log the MongoDB query dictionary being used.
- Log the number of records returned from the query.

#### [MODIFY] [__init__.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models/__init__.py)
- Add `ClientAccountID` as an additional alias for `account_id` in the `TradeRecord` model to ensure it is captured correctly from different IBKR report formats.

### Data Ingestion and Cleanup

#### [MODIFY] [ingest_legacy_trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/ingest_legacy_trades.py)
- Explicitly map `ClientAccountID` to `AccountId` during ingestion if it exists.

#### [NEW] [cleanup_trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/scripts/cleanup_trades.py)
- A script to identify and remove trades missing critical information or fix those missing `AccountId` by re-processing source files.

## Verification Plan

### Automated Tests
- Run existing trade tests to ensure no regressions:
  ```bash
  pytest tests/test_api_trades.py
  ```

### Manual Verification
1. Check backend logs after making requests to `http://localhost:8000/api/trades/` and `http://localhost:8000/api/trades/analysis`.
2. Verify that the `TRADES` view in the frontend shows account data after cleanup/fix.
3. Run the cleanup script/command and verify the output.
