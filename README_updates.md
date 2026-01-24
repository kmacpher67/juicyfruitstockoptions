# Project Updates

## 2026-01-16: Running Averages Fix

- **Feature**: Implementing standard Simple Moving Average (SMA) calculation using pandas `rolling().mean()`.
- **Fix**: Updated `stock_live_comparison.py` to automatically detect and re-fetch data for tickers that have missing Moving Average values (NaN), ensuring the Excel output is fully populated.
- **Usage**: No change in usage command. `python stock_live_comparison.py` will now automatically handle missing MAs.

## 2026-01-16: Refactoring and Testing

- **Refactor**: Extracted hardcoded ticker list in `stock_live_comparison.py` to `StockLiveComparison.get_default_tickers()` method for better testability.
- **Testing**: Added `test_stock_ticker_list.py` to verify ticker list integrity.
- **Config**: Added `pytest.ini` to properly configure pytest and exclude `mongo_data` directory from test collection.
- **Feature**: Added Google Finance hyperlinks to the Ticker column in the generated Excel output.
