# Dividend Feed Fixes (2026-03-05)

## Goal Description
Address two user issues on the Dividend Feed:
1. "Why is still OLN xdiv which 03/03 already pass?" - Ex-dividend dates from persisted scans are not filtered for dates >= today.
2. "Why only 4 upcoming, I'd like all stock tickers in the tracker not just portfolio" - The scanner currently limits the ticker scan list to only those held in the portfolio (`ibkr_holdings`).

## Proposed Changes

### Backend Modifications
#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **Filter past ex-dividend dates:** In the `scan_dividend_capture` endpoint (when `force_scan=False`), parse the returned `opportunities` from `OpportunityService`, looking at `proposal["ex_date"]` and excluding any records where the date is strictly less than today's date formatted as `YYYY-MM-DD`.
- **Expand Ticker Scanning Pool:** In the `scan_dividend_capture` endpoint (when `force_scan=True`), query `db.stock_data` to fetch all tracked stock tickers (e.g., `db.stock_data.distinct("Ticker")`) and combine them with the portfolio symbols before submitting to `scan_dividend_capture_opportunities(symbols)`.

### Test Script Additions
#### [NEW] [api_tests.http](file:///home/kenmac/personal/juicyfruitstockoptions/tests/api_tests.http)
- Created an HTTP test file providing endpoints for API requests (`GET /analysis/dividend-capture`, `/analysis/dividend-capture?force_scan=true`), securely extracting and applying the authentication token automatically.

## Verification Plan

### Automated Tests
- **Pytest:** Add unit tests to verify that `scan_dividend_capture` properly omits historical dates. Execute `pytest tests/test_dividend_capture_analysis.py` (or related test suites) and ensure new lines are covered.
- Check test coverage via `pytest --cov=app/api/routes.py`.

### Manual Testing
- Run `tests/api_tests.http` utilizing VS Code REST Client or Bruno to manually fetch the endpoint and ensure the payload includes tickers beyond just the portfolio and drops past dates.
