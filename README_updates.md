# Project Updates

## 2026-03-30: IBKR Client Portal Fallback

- **Infrastructure**: Added an `ibkr-portal` Docker Compose service that runs the bundled `clientportal.gw` gateway on port `5000`.
- **Backend**: Added `app/services/ibkr_portal_service.py` with session-aware `keepalive()`, `get_positions()`, and `get_summary()` methods behind the `IBKR_PORTAL_ENABLED` feature flag.
- **CLI**: Added `python -m app.scripts.ibkr_portal_cli` for manual status, keepalive, positions, and summary checks.
- **Testing**: Added unit coverage for disabled mode, keepalive, account discovery, and summary fetching.

## 2026-01-16: Running Averages Fix

- **Feature**: Implementing standard Simple Moving Average (SMA) calculation using pandas `rolling().mean()`.
- **Fix**: Updated `stock_live_comparison.py` to automatically detect and re-fetch data for tickers that have missing Moving Average values (NaN), ensuring the Excel output is fully populated.
- **Usage**: No change in usage command. `python stock_live_comparison.py` will now automatically handle missing MAs.

## 2026-01-16: Refactoring and Testing

- **Refactor**: Extracted hardcoded ticker list in `stock_live_comparison.py` to `StockLiveComparison.get_default_tickers()` method for better testability.
- **Testing**: Added `test_stock_ticker_list.py` to verify ticker list integrity.
- **Config**: Added `pytest.ini` to properly configure pytest and exclude `mongo_data` directory from test collection.
- **Feature**: Added Google Finance hyperlinks to the Ticker column in the generated Excel output.
