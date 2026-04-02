# Walkthrough: Portfolio Live Grid 001/002 Regression Lock (2026-04-02)

## Scope

Completed:

- `portfolio-live-grid-001`
- `portfolio-live-grid-002`

## Implementation

- Extracted shared number/formatting guards to:
  - `frontend/src/components/portfolioGridFormatters.js`
- Updated `PortfolioGrid.jsx` to use shared formatter utilities:
  - `getNumericValue`
  - `formatCurrency`
  - `formatPercent`

This keeps the fallback contract centralized and testable.

## Regression Tests Added

- `frontend/src/components/portfolioGridFormatters.test.js`
  - Verifies undefined-like and non-finite values map to `-`
  - Verifies currency formatter does not emit literal `undefined`/`NaN`
  - Verifies percent formatter does not emit `NaN%`
  - Verifies valid numeric formatting still works

## Verification

- `node --test frontend/src/components/portfolioFilters.test.js frontend/src/components/portfolioGridFormatters.test.js`

Passed.
