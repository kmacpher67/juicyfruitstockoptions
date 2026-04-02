# Walkthrough: F-R Low-Hanging Fruit Pass (2026-04-02)

## Scope Completed

This pass implemented and verified the following F-R items:

1. `events-stk-filter-bug`
2. `trade history / dividends -> Backend Parser`
3. `portfolio-coverage-004`
4. `portfolio-export-004`

## Code Changes

- `app/services/dividend_scanner.py`
  - Added symbol normalization logic so option contract symbols are filtered to underlying STK tickers before any `yfinance` lookup.
  - Updated dividend scan flow to dedupe normalized symbols and skip non-equity symbols.
  - Tightened holdings mapping for dividend scan context to avoid option rows polluting account holdings strings.

## Test Coverage Added

- `tests/test_dividend_capture_analysis_v2.py`
  - Added regression: scanner filters option symbols (e.g. OCC option contracts) before calling `yfinance`.

- `tests/test_ibkr_service_dividends.py`
  - Added parser coverage for `parse_csv_dividends`:
    - `PO` and `RE` row handling
    - date normalization to `YYYY-MM-DD`
    - `action_id` upsert key behavior
    - compound fallback key when `action_id` is missing

- `tests/test_portfolio_enrichment.py`
  - Added explicit `(account, underlying)` coverage-status regression:
    - `U110638` + `AMD` + `200` shares with `-2` short calls => `Covered`

- `frontend/src/components/portfolioFilters.test.js`
  - Added export-alignment regression tests for combined filter logic:
    - `Expiring + Near Money + Coverage + Account + Show STK=true`
    - same combination with `Show STK=false`

## Verification Commands

- `pytest -q tests/test_ibkr_service_dividends.py tests/test_dividend_capture_analysis_v2.py tests/test_portfolio_enrichment.py -k "dividends or filters_option_symbols or 200_shares_and_2_short_calls"`
- `node --test frontend/src/components/portfolioFilters.test.js`

Both commands passed.
