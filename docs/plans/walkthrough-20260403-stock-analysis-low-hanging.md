# Walkthrough: Stock Analysis Low-Hanging Batch (2026-04-03)

## Scope

Focused pass on the in-progress stock-analysis items from `docs/features-requirements.md`:

1. `stock-analysis-broken-202603`
2. `stock-analysis-report-churn-20260402`
3. `stock-analysis-valid-source-file-guard-20260403` (new)
4. `stock-analysis-trigger-policy-tests-20260403` (new)
5. `Tickers — Composite Rating`
6. `All ~40 Columns in Analytics Tab`
7. Frontend logging: React Error Boundary

## Changes

### Backend

- `stock_live_comparison.py`
  - Added `is_viable_spreadsheet_file()` and `get_latest_viable_spreadsheet()` to avoid using suspiciously small XLSX files as merge source.
  - `run()` now prefers `latest_viable_file` for merge, with warning logs when the newest file fails viability guard.
  - Added `is_suspicious_record_count()` and fail-safe abort before save if result size is unexpectedly tiny versus tracked ticker count.
- `app/services/stock_live_comparison.py`
  - Added sync-mode viability gating: when trigger is `sync`, the service now skips work if no viable existing report exists, preventing accidental file creation/churn in background paths.

### Frontend

- `frontend/src/components/stockAnalysisPresentation.js` (new)
  - Shared analytics-field groups for Ticker Modal.
  - Composite ticker-health score and tone/label helpers (technical + optional sentiment/macro inputs).
- `frontend/src/components/TickerModal.jsx`
  - Analytics tab now renders the full stock-analysis field set through shared groups.
- `frontend/src/components/StockGrid.jsx`
  - Added sortable, color-coded `Ticker Health` column.
- `frontend/src/components/errorLogging.js` + `AppErrorBoundary.jsx` (new)
  - Structured frontend error payload builder and dashboard error boundary.
- `frontend/src/App.jsx`
  - Wrapped dashboard route in `AppErrorBoundary`.

### Docs

- `docs/features-requirements.md`
  - Marked selected stock-analysis items as `[/]` in progress.
  - Marked trigger-policy sub-items complete where implemented/tested.
  - Added two new in-progress F-R entries for source-file viability guard and trigger policy regression coverage.

## Tests Added/Updated

- `tests/test_stock_live_methods.py`
  - `test_get_latest_viable_spreadsheet_skips_small_files`
  - `test_run_uses_latest_viable_file_as_merge_source`
  - `test_run_rejects_suspiciously_small_result_set`
- `frontend/src/components/stockAnalysisPresentation.test.js` (new)
  - Coverage for full analytics field mapping and ticker-health scoring/tone including sentiment/macro inputs.
- `frontend/src/components/errorLogging.test.js` (new)
  - Coverage for structured error payload generation.
- `tests/test_stock_live_comparison_service.py`
  - Added sync-trigger regression ensuring no run occurs when no viable report exists.

## Verification Commands

- `pytest -q tests/test_stock_live_methods.py`
- `pytest -q tests/test_stock_live_comparison_service.py tests/test_stock_live_routes_manual_trigger.py`
- `node --test frontend/src/components/stockAnalysisPresentation.test.js frontend/src/components/errorLogging.test.js frontend/src/components/tickerModalHeader.test.js`

## F-R Status Update

Completed in this pass (`[x]`):
- `stock-analysis-broken-202603`
- `stock-analysis-report-churn-20260402`
- `stock-analysis-valid-source-file-guard-20260403`
- `stock-analysis-trigger-policy-tests-20260403`
- `Stock Analysis -> Bug fix entire feature quit working`
- `Stock Analysis -> Report file lifecycle policy`
- `Tickers — Composite Rating`
- `All ~40 Columns in Analytics Tab`
