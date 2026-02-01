# Implementation Plan - Restrict Deletion & Fix Option Underlying Discovery

I will address the user's request to prevent deletion of portfolio items on the Analysis screen and ensure underlying stocks for options (like CPRX) are automatically tracked.

## User Review Required

> [!IMPORTANT]
> I will be modifying the "Lazy Sync" logic in `app/api/routes.py`. This will automatically add any underlying stocks found in your portfolio options to your "Tracked Tickers" list. This means if you trade options on a new stock, that stock will appear in your Analysis dashboard automatically.

## Proposed Changes

### Frontend - Prevent Deletion
#### [MODIFY] [StockGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/StockGrid.jsx)
- Update `ActionsRenderer` to check if the ticker is in `portfolioTickers`.
- If it is a portfolio ticker, do not render the Delete button (or render a disabled state/lock icon).
- This ensures users cannot inadvertently remove items that are actively in their portfolio.

### Backend - Fix Missing Underlying Logic
#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- In the `get_tracked_tickers` endpoint (Lazy Sync logic):
    - Currently, it only queries `distinct("symbol")` from `ibkr_holdings`.
    - I will add a query for `distinct("underlying_symbol")` as well.
    - I will merge these two sets to ensure tickers like `CPRX` (which may only exist as `underlying_symbol` for an option contract) are included in the `new_tickers` list.
    - This aligns with the "yahoo ticker export" logic mentioned by the user.

#### [MODIFY] [jobs.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/scheduler/jobs.py)
- Incorporate the "Lazy Sync" logic into the daily scheduled job.
- Ensure that `stock_live_comparison` or the ticker syncer logic runs as part of the daily startup routine (e.g., `run_daily_job`).
- This guarantees that new portfolio items (like `CPRX` options) are picked up automatically every morning without requiring a manual UI refresh.

## Verification Plan

### Automated Tests
- **Backend Logic**: I will create a temporary reproduction script `tests/verify_routes_logic.py` that connects to the database, runs the improved distinct query logic, and verifies that `CPRX` (or other option underlyings) are returned.
- **Frontend**: I will verify the code changes by inspection (as I cannot easily run interactive UI tests in this environment).

### Manual Verification
- **Run `get_tracked_tickers`**: I will trigger the API logic (via script or curl) and check if `CPRX` is added to `tracked_tickers` in MongoDB.
- **Check Analysis Screen**: After the backend update, reloading the Analysis screen (which calls this endpoint) should populate the missing tickers.
