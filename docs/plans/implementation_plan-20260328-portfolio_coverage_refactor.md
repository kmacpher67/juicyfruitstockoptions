# Implementation Plan - Portfolio Coverage Refactor – Bug Fix (2026-03-28)

## Root Cause

The IBKR CSV parser (`parse_csv_holdings`) stores raw CSV field names as-is. IBKR uses `AssetClass` (PascalCase). However, the coverage aggregation in `routes.py` (line 591) only checked `asset_class`, `secType`, and `sec_type` — **never `AssetClass`**.

This meant **STK rows were never identified**, so shares were never accumulated. The result:
- Stocks with no options: `shares=0, short_calls=0` → `0 == 0` → **"Covered"** (wrong, should be Uncovered)
- Stocks with options: `shares=0, short_calls=N` → `0 < N` → **"Naked"** (wrong, should be Covered or Uncovered)

## Fix

Added `"AssetClass"` to the field lookup chain in both `sec_type` resolutions (lines 591 and 640):

```python
sec_type = row.get("asset_class") or row.get("AssetClass") or row.get("secType") or row.get("sec_type")
```

## Regression Test

Added `test_get_portfolio_holdings_coverage_with_ibkr_pascal_case_asset_class` covering:
- AMD (200 shares, 0 calls) → Uncovered
- OLN (100 shares, 1 call) → Covered
- ERO (300 shares, 2 calls) → Uncovered

## Change Log

| Date | Action | Reason |
|------|--------|--------|
| 2026-03-28 | FIX | Added `AssetClass` PascalCase to sec_type lookups in coverage logic |
| 2026-04-02 | FIX | Count short calls from normalized option metadata (`right`, parsed OCC fields, `local_symbol`) so TWS/live rows with `symbol=AMD` still contribute to coverage totals |

## Follow-Up Regression (2026-04-02)

### Trigger

In `?view=PORTFOLIO`, account `U110638` showed AMD as `Uncovered` while holding:

- `200` AMD shares
- `-1` AMD `2026-04-02 202.5 Call`
- `-1` AMD `2026-04-10 207.5 Call`

This position should be `Covered` because `200 == abs((-1 + -1) * 100)`.

### Root Cause

The coverage aggregation recognized short calls only when `row["symbol"]` matched an OCC call pattern. That worked for Flex-style option rows such as `AMD  260402C00202500`, but failed for TWS/live rows where:

- `symbol` is just the underlying root, for example `AMD`
- the option contract identity is stored in `local_symbol`, `right`, `strike`, and expiry fields

As a result, TWS short calls were skipped during coverage aggregation, producing `shares=200` and `short_calls=0`, which incorrectly resolved to `Uncovered`.

### Fix

- Detect short calls from normalized option metadata, not only from `symbol`
- Accept any of the following as evidence that a negative option row is a short call:
  - `right == "C"`
  - parsed OCC fields resolve to call
  - `local_symbol` or `symbol` contains a call OCC pattern

### Regression Test

Added `test_get_portfolio_holdings_counts_tws_local_symbol_short_calls_for_covered_status` covering the exact `U110638` / AMD scenario with:

- `200` stock shares
- two separate TWS short call rows
- expected `Covered` status on the stock row and both option rows

Refactor the portfolio coverage logic to provide granular filtering for "Covered", "Uncovered", and "Naked" positions, resolving the issue where the "Uncovered" filter was too broad.

## Proposed Changes

### Backend

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- Refine the `coverage_status` logic in `get_portfolio_holdings` to strictly follow the provided mathematical definitions:
    - **Covered**: `shares == covered_shares` (where `covered_shares` is `abs(SHORT_CALL_QTY) * 100`)
    - **Uncovered**: `shares > covered_shares`
    - **Naked**: `shares < covered_shares` (includes cases with 0 shares and negative calls)
- The logic will be applied at the (Account, Underlying) granularity.
- Keep `coverage_mismatch` as a boolean flag for UI highlighting, but remove it from the filtering logic in the frontend.

### Frontend

#### [MODIFY] [PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/PortfolioGrid.jsx)
- Update the focus filtering logic:
    - `uncovered`: Filter specifically for `coverage_status === 'Uncovered'`.
    - `naked`: New filter for `coverage_status === 'Naked'`.
    - `covered`: New filter for `coverage_status === 'Covered'`.
- Update the UI toolbar to include these filter buttons and treat coverage status as one filter dimension.
- Make `Expiring (<ND)`, `Near Money (<N%)`, and `Account` combine with the selected coverage status using logical `AND` semantics.
- Add a configurable Near Money threshold selector with default `8`, allowed range `0` to `20`, and dynamic button text.
- Add a toolbar row counter that reflects the currently visible filtered result set.
- Define Near Money from underlying stock price vs option strike using absolute percentage distance in either direction around the strike. Do not use option premium as the reference value.
- Ensure the `All` action clears all active filter dimensions and restores the default `DTE=6`.
- Extract the filter predicate into a small pure helper so regression tests can validate the combined filtering contract without a browser runner.

## Verification Plan

### Automated Tests
- Run existing tests to ensure no regressions:
  `pytest tests/test_portfolio_enrichment.py`
- Add frontend filter regression coverage for combined `AND` filtering:
  `node --test frontend/src/components/portfolioFilters.test.js`

### Manual Verification
- Start the dev server: `npm run dev` in `frontend` and the FastAPI server.
- Navigate to the Portfolio holdings view.
- Click the "Uncovered" button and verify it ONLY shows positions with `coverage_status === 'Uncovered'`.
- Click the "Naked" button and verify it shows positions with `coverage_status === 'Naked'`.
- Click the "Covered" button and verify it shows positions with `coverage_status === 'Covered'`.
- Turn on `Expiring (<ND)` and verify it narrows the current coverage selection instead of replacing it.
- Turn on `Near Money (<8%)` and verify it further narrows the result set instead of replacing the other filters.
- Change the Near Money percent value and verify the visible rows update to reflect the selected threshold.
- Verify that a contract such as AMD `202.5C` with underlying around `210.21` reports roughly `3.7%` distance, not `95%+`.
- Select an account and verify the visible rows satisfy coverage status, DTE, near-money, and account simultaneously.
- Verify the row counter matches the number of visible rows after filtering.
- Verify that the `All` button resets filters.
