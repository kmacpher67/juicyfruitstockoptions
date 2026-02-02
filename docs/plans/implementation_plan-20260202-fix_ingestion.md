# Fix Option Data Ingestion for Smart Rolls

## Goal
Enable "Smart Roll" analysis by fixing the data ingestion pipeline (`ibkr_service.py`) to correctly capture Option details (Expiry, Strike, Put/Call) from IBKR Flex Reports, which are currently being ignored.

## User Review Required
> [!IMPORTANT]
> **Flex Query Configuration**: This fix assumes your IBKR Flex Query includes the following fields: `Expiry`, `Strike`, `Put/Call` (or `Right`), and `AssetClass`. If these metrics are missing from your report configuration in IBKR, the code will still fail to find them. Please ensure your Flex Query includes these fields.

## Proposed Changes

### Backend (`app/services`)

#### [MODIFY] [ibkr_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/ibkr_service.py)
#### [MODIFY] [ibkr_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/ibkr_service.py) [COMPLETED]
- Update `parse_csv_holdings` and `parse_xml_holdings`:
  - **Logic Update**: If `asset_class` is "OPT" or "FOP", or if the `Symbol` looks like an OCC string (21 chars, spaces, numbers):
    - Parse the `Symbol` string (e.g., `AMD   260206C00230000`) to extract:
      - `underlying_symbol` (e.g. AMD)
      - `expiry` (YYMMDD -> YYYY-MM-DD)
      - `right` (C/P)
      - `strike` (Divide by 1000)
    - Store these as top-level fields in the MongoDB document: `expiry`, `strike`, `right`, `secType`="OPT".
    - This ensures `RollService` finds the data without requiring changes to the user's Flex Query columns (assuming Symbol is standard).

#### [MODIFY] [roll_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/roll_service.py) [COMPLETED]
- Update `analyze_portfolio_rolls`:
  - Accept `asset_class` == "OPT" as equivalent to `secType` == "OPT".
  - Handle `right` == "P"/"C" or "Put"/"Call" normalization.

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py) [COMPLETED]
- Remove authentication from `/calendar/dividends.ics` to facilitate browser/calendar subscription.

## Verification Plan

### Automated Tests
- Create a test case with a sample CSV line containing Option data.
- Verify `ibkr_service` parses `expiry`, `strike`, and `right` correctly.
- Verify `RollService` accepts this new data structure.

### Manual Verification
- Run `debug_rolls.py` again.
- If data is still missing (because database snapshot is old), Trigger a fresh IBKR Sync (if token is available and safe) OR manually insert a mock record into Mongo to verify `RollService` finds it.
