# Goal Description

The user requested enhancements to the Trades Query data synchronization and its display under "view=TRADES" (the `/api/trades/` endpoint which fetches raw trades). Specifically:
1. Explain/Schedule the Trades Query to update the Mongo DB collection for all Accounts.
2. Fix `AssetClass` (STK vs OPT) not displaying correctly.
3. Add missing `Put/Call` field.
4. Show `NetCash` column.
5. Show `ClosePrice` column next to `NetCash`.
6. Show `Exchange` as the last column.

## User Review Required

No major architectural shifts. Note that for existing trades in the MongoDB `ibkr_trades` collection, these new fields (`asset_class`, `put_call`, `net_cash`, `close_price`) won't magically appear until the next IBKR Flex Daily sync overwrites them, or unless a historical sync script is run. Is this acceptable? Let me know if you need me to write a script to backfill these fields from historical CSV files.

## Proposed Changes

---
### app/models/__init__.py
Update the `TradeRecord` Pydantic model so that the new fields are formally exposed by the API when frontend applications query `/api/trades`. Pydantic preserves field definition order for dictionary serialization, so we will place them appropriately to satisfy the "ClosePrice next to NetCash" and "Exchange as last column" requests.

#### [MODIFY] app/models/__init__.py
- Add `asset_class: Optional[str] = Field(None, alias="AssetClass")` to `TradeRecord`.
- Add `put_call: Optional[str] = Field(None, alias="Put/Call")` to `TradeRecord`.
- Add `net_cash: Optional[float] = Field(None, alias="NetCash")` to `TradeRecord`.
- Add `close_price: Optional[float] = Field(None, alias="ClosePrice")` to `TradeRecord` (right after `net_cash`).
- Move the existing `exchange: Optional[str] = None` to the very bottom of the `TradeRecord` class definition to ensure it serializes last.

---
### app/services/ibkr_service.py
Enhance the ingestion logic to parse and persist these new fields into MongoDB.
Add logging to debug the trades sync process (name of local file and number of records)

#### [MODIFY] app/services/ibkr_service.py
- **In `parse_csv_trades`**:
  - Extract `AssetClass` -> `doc["asset_class"]`
  - Extract `Put/Call` -> `doc["put_call"]`
  - Extract `NetCash` -> `doc["net_cash"]`
  - Extract `ClosePrice` -> `doc["close_price"]`
- **In `parse_xml_trades`**:
  - Extract `assetCategory` -> `doc["asset_class"]`
  - Extract `putCall` -> `doc["put_call"]`
  - Extract `netCash` -> `doc["net_cash"]`
  - Extract `closePrice` -> `doc["close_price"]`

---
### app/scheduler/jobs.py & Documentation
Address the scheduling question.
- **Context**: The application already uses `APScheduler` in `app/scheduler/jobs.py` which runs the `run_ibkr_sync()` job every day (default 10:00 AM, configurable in DB). The `run_ibkr_sync()` function automatically fetches the query ID configured in `query_id_trades` (i.e. the Trades Query) and saves trades for all accounts.
- **Action**: I will verify that this setup satisfies the requirement. No new code is strictly required for scheduling *unless* the user wants a separate trigger. I will add comments to `scheduler.py` emphasizing the Trades sync.

---
### docs/features-requirements.md
Update the checklist to reflect that the Trades Query parsing has been expanded and mapped to the API models.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_api_trades.py` and ensure the API successfully returns the new columns in the expected order.
- Create tests/check existing tests verifying `parse_csv_trades` and `parse_xml_trades` specifically capture the 4 new metrics, using the `data/ibkr_data/trades/` sample files. (We are subject to 100% test coverage for Finance).

### Manual Verification
1. Open the UI / trigger `/api/trades` locally.
2. Trigger an ad-hoc sync or test script that parses a recent CSV.
3. Validate that the JSON payload returns `asset_class`, `put_call`, `net_cash`, `close_price`, and `exchange` (as the final key).
