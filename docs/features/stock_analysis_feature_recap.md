# Stock Analysis Feature Recap

> **Date:** 2026-03-28  
> **Status:** Bug Investigation — Feature Broken  
> **Referenced Bug:** `features-requirements.md` L108-L114

---

## What This Feature Does

The **Stock Analysis** feature is the core research tool of the Juicy Fruit dashboard. It:

1. **Fetches live stock data** for a tracked ticker list using Yahoo Finance (`yfinance`)
2. **Computes ~40 metrics per ticker**, including:
   - Price data: Current Price, 1D % Change, YoY Price %
   - Technical indicators: EMA_20, HMA_20, TSMOM_60, RSI_14, ATR_14, MA_30/60/120/200
   - Options analysis: Call/Put Skew, 3-mo/6-mo/1-yr Call Yield, 1-yr 6% OTM PUT Price
   - Fundamentals: P/E, Market Cap, Div Yield, Analyst Target, Ex-Div Date
   - Highlight columns: delta % for each MA/EMA vs current price
   - Price Action analysis via `PriceActionService`
   - Internal date columns for Yahoo Finance option chain links
3. **Generates an Excel spreadsheet** (`AI_Stock_Live_Comparison_YYYYMMDD_HHMMSS.xlsx`) with:
   - Conditional formatting (green/red) for skew, MAs, EMA, HMA, TSMOM
   - Hyperlinks to Google Finance (Ticker column) and Yahoo Finance option chains
   - Frozen header row, sorted by Last Update desc
4. **Upserts all data to MongoDB** (`stock_data` collection) for API consumption
5. **Exports a JSON backup** for git versioning

### Data Flow Architecture

```
User clicks "Run Live Comparison" button
        │
        ▼
Dashboard.jsx → POST /api/run/stock-live-comparison
        │
        ▼
routes.py → BackgroundTasks → run_stock_live_comparison()
        │
        ▼
StockLiveComparison.run()
  ├── Reads latest existing Excel (if any)
  ├── Identifies missing/outdated tickers
  ├── Fetches via yfinance (download + Tickers API)
  ├── Merges with preserved existing records
  ├── Adds Call/Put Skew column
  ├── Saves to Excel with formatting
  ├── Upserts to MongoDB
  └── Exports JSON backup
        │
        ▼
Dashboard.jsx polls /api/jobs/{id} until complete
        │
        ▼
Dashboard.jsx → GET /api/reports (lists Excel files)
Dashboard.jsx → GET /api/reports/{filename}/data (reads Excel → JSON)
        │
        ▼
StockGrid.jsx renders data in ag-Grid with ~10 column definitions
```

---

## Expected Columns (All ~40)

As documented in `features-requirements.md` L112:

| Category | Columns |
|:---|:---|
| **Identity** | Ticker |
| **Price** | Current Price, 1D % Change, Market Cap (T$), P/E, YoY Price % |
| **Technical Indicators** | EMA_20, HMA_20, TSMOM_60, RSI_14, ATR_14 |
| **Moving Averages** | MA_30, MA_60, MA_120, MA_200 |
| **Highlights (delta %)** | EMA_20_highlight, HMA_20_highlight, TSMOM_60_highlight, MA_30/60/120/200_highlight |
| **Dividends** | Ex-Div Date, Div Yield |
| **Analyst** | Analyst 1-yr Target |
| **Options — Puts** | 1-yr 6% OTM PUT Price, Annual Yield Put Prem |
| **Options — Calls** | 3-mo Call Yield, 6-mo Call Yield, 1-yr Call Yield, Annual Yield Call Prem |
| **Skew** | Call/Put Skew |
| **Internal** | 6-mo Call Strike, Error, Last Update, _PutExpDate_365, _CallExpDate_365, _CallExpDate_90, _CallExpDate_180 |

---

## Root Cause Analysis

### Finding 1: User-triggered runs produce truncated Excel files

| Source | Owner | File Size | Works? |
|:---|:---|:---|:---|
| Docker cron (scheduled) | `root` | ~40 KB | ✅ Full data |
| FastAPI API (user click) | `kenmac` | ~6 KB | ❌ Truncated |

**Evidence:** All files from Mar 25-28 owned by `kenmac` (user-triggered via "Run Live Comparison" button) are ~6KB. Files owned by `root` (Docker cron scheduled runs) are ~40KB with full data.

**Likely Cause:** The `StockLiveComparison.run()` method merges new fetched data with existing Excel data. When the user triggers a run:
- The `get_latest_spreadsheet()` picks up the latest file (which may be a previously truncated 6KB file)
- The `get_missing_or_outdated_tickers()` finds most tickers "up to date" in the truncated file
- Result: only a few tickers get re-fetched, producing another small file
- **Snowball effect**: Each subsequent run reads the previous small file and produces another small file

Additionally, the `background_job_wrapper` in `routes.py` **calls `run_stock_live_comparison` twice** (lines 140 and 143), creating duplicate background tasks and potential race conditions.

### Finding 2: StockGrid.jsx only renders ~10 columns

The frontend `StockGrid.jsx` has **never** had all ~40 columns. Git history shows it was created with ~9 columns at commit `f150ed2` and has only changed slightly since. Current `baseDefs` only includes:

- Ticker, Current Price, Call/Put Skew, 1D % Change, YoY Price %, TSMOM_60, MA_200, EMA_20, HMA_20, Div Yield

The `AVAILABLE_COLUMNS` array in `Dashboard.jsx` (L16-27) mirrors the same limited set.

> [!IMPORTANT]
> This means the frontend never showed all 40 columns in the HTML grid view. The full column set was only visible in the **downloaded Excel spreadsheet**. The feature "quit working" because the Excel files became truncated due to Finding 1.

---

## Key Source Files

| File | Role |
|:---|:---|
| [stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py) | Main backend class — fetches data, computes metrics, generates Excel |
| [app/services/stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/stock_live_comparison.py) | Service wrapper called by API |
| [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py) | API endpoints: `/run/stock-live-comparison`, `/reports`, `/reports/{filename}/data` |
| [frontend/src/components/StockGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/StockGrid.jsx) | Frontend grid — 10 hardcoded columns |
| [frontend/src/components/Dashboard.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/Dashboard.jsx) | Dashboard — controls, report selector, `AVAILABLE_COLUMNS` |
| [tests/test_stock_live_methods.py](file:///home/kenmac/personal/juicyfruitstockoptions/tests/test_stock_live_methods.py) | Backend unit tests for StockLiveComparison |

---

## How to Recreate / Fix

### Bug Fix 1: Prevent truncated Excel snowball (Backend)

1. **Remove duplicate background task** in `routes.py` (lines 140+143 — `run_stock_live_comparison` is added twice)
2. **Fix `get_latest_spreadsheet()`** to prefer files above a minimum size threshold (e.g., >10KB) to avoid snowballing from truncated files
3. **Add validation in `run()`** — after building `final_records`, if the record count is suspiciously low (e.g., <5 when ticker list has 80+), log a warning and skip saving to avoid overwriting good data with bad
4. **Root cause**: Investigate why `yfinance` calls fail in the FastAPI context but succeed in Docker cron. Possible issues: rate limiting, network config, missing environment variables

### 2026-04-03 follow-up fix (429 throttling)

- Fixed `fetch_data()` retry behavior in `stock_live_comparison.py`.
- Previous logic had a retry loop that never incremented attempts and marked first failure as final, so `HTTP 429` could not recover.
- New behavior:
  - bounded retry attempts for ticker-level fetches,
  - exponential backoff for retryable yfinance/network errors,
  - final error record only after retries are exhausted.
- Added regression coverage in `tests/test_stock_live_methods.py::test_fetch_data_retries_on_429_and_recovers`.

### Bug Fix 2: Add all columns to StockGrid.jsx (Frontend)

1. **Update `baseDefs`** in `StockGrid.jsx` to include all ~40 columns with proper formatting
2. **Update `AVAILABLE_COLUMNS`** in `Dashboard.jsx` to include all columns
3. Consider making the grid columns **dynamic** — auto-generate column definitions from the API response data keys

### Verification

1. Run existing tests: `pytest tests/test_stock_live_methods.py -v`
2. Manually trigger "Run Live Comparison" and verify the generated Excel file has ~40 columns and 80+ rows
3. Verify the frontend grid displays all columns
4. Compare with a known-good Docker cron file (~40KB)

---

---

## Stuck-Button Recovery (run-obs-004)

**Problem:** When a stock-live-comparison job gets stuck or stale, the Run button stays grayed out indefinitely. The original code only cleared `running` state when the specific job-id poll returned `completed` or `failed` — it never consulted the latest-job endpoint to reconcile after a page reload or timer loss.

**Fix (2026-04-07):**

- `Dashboard.jsx` now calls `GET /api/jobs/latest/stock-live-comparison` once on mount (via a `useEffect`) to pre-populate the button state. If the server reports `"running"`, the watchdog interval starts immediately.
- A 15-second watchdog `setInterval` (stored in `watchdogIntervalRef`) polls the latest-job endpoint while `running === true`. When the endpoint returns any terminal status (`completed`, `failed`, `timed_out`, `stale_watchdog_failed`), the button is re-enabled and a short reason string is displayed inline.
- `runObsUtils.js` extracts the pure `deriveRunButtonState(job)` and `fetchLatestJob(token)` helpers so the logic is testable without a DOM.
- The watchdog interval ref is cleared in the `useEffect` cleanup to prevent leaks on unmount.

**Status reason text displayed near the button:**

| Server status | Button | Label shown |
|:---|:---|:---|
| `running` | Disabled | Analysis running... |
| `completed` | Enabled | (none) |
| `failed` | Enabled | Previous run failed -- ready to retry |
| `timed_out` | Enabled | Previous run timed out -- ready to retry |
| `stale_watchdog_failed` | Enabled | Stale run cleared -- ready to retry |

**Files changed:**
- `frontend/src/components/Dashboard.jsx` — watchdog `useEffect`, `runStatusLabel` state, updated `runAnalysis`
- `frontend/src/components/runObsUtils.js` — shared pure helpers (new)
- `frontend/src/components/runObsUtils.test.js` — 15 Node test cases (new)

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-03-28 | **CREATED** | Initial feature recap documenting Stock Analysis breakage root cause |
| 2026-04-03 | **UPDATED** | Documented yfinance 429 retry-loop fix and added regression test coverage |
| 2026-04-07 | **UPDATED** | Documented stuck-button recovery behavior (run-obs-004) |
