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
- Update the UI toolbar to include these new filter buttons.
- Ensure the "All" default works as expected.

## Verification Plan

### Automated Tests
- Run existing tests to ensure no regressions:
  `pytest tests/test_portfolio_enrichment.py`
- Update `tests/test_portfolio_enrichment.py` to verify the more granular status logic if needed.

### Manual Verification
- Start the dev server: `npm run dev` in `frontend` and the FastAPI server.
- Navigate to the Portfolio holdings view.
- Click the "Uncovered" button and verify it ONLY shows positions with `coverage_status === 'Uncovered'`.
- Click the "Naked" button and verify it shows positions with `coverage_status === 'Naked'`.
- Click the "Covered" button and verify it shows positions with `coverage_status === 'Covered'`.
- Verify that the "All" button resets filters.
