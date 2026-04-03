# Walkthrough: Low-Hanging Follow-Up (2026-04-03)

## Scope

Focused pass on three small F-R items:

1. `portfolio-last-price-002` (explicit Min/Max last-price filter controls)
2. `ibkr-orders-005` (order-normalization regression coverage)
3. `Dividend Feed` UI fallback bug (empty/undefined Holdings/Predicted/Target/Return rendering)

## Changes

### Frontend

- `frontend/src/components/portfolioFilters.js`
  - Added `lastPriceMin` / `lastPriceMax` to default filter state.
  - Added last-price range filtering in `rowMatchesPortfolioFilters` using shared numeric normalization.
  - Supports `market_price`, `last_price`, `current_price`, or `price` field names.

- `frontend/src/components/PortfolioGrid.jsx`
  - Added toolbar controls for `Last Price` min/max.
  - Uses shared filter state so on-screen rows and CSV export stay aligned.

- `frontend/src/components/dividendPresentation.js` (new)
  - Added formatting/fallback helpers for currency, percent, holdings list parsing, predicted-price fallback, analyst-target fallback, and quarterly-return fallback.

- `frontend/src/components/DividendListModal.jsx`
  - Switched Holdings/Predicted/Target/Return/Yield cells to safe format helpers.
  - Eliminates `$undefined` output and preserves display when values are missing.

### Backend Tests

- `tests/test_api_orders.py`
  - Added normalization regression coverage for:
    - OCC option-symbol parsing + inferred display symbol
    - `BOT`/`SLD` action normalization
    - `remaining_quantity` fallback computation
    - roll-like paired orders retained as separate actionable rows

### Frontend Tests

- `frontend/src/components/portfolioFilters.test.js`
  - Added tests for last-price range filtering and AND-combination behavior with existing filters.

- `frontend/src/components/dividendPresentation.test.js` (new)
  - Added tests for fallback formatting and return/target/prediction resolution.

## F-R Updates

- `docs/features-requirements.md`
  - Marked `Last Price` and `portfolio-last-price-002` as complete.
  - Marked dividend-feed Yahoo-link item complete.
  - Updated dividend-feed bug item to reflect UI fallback fix and remaining return-definition follow-up.
