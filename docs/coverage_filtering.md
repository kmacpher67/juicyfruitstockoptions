# Portfolio Coverage And Focus Filtering

This document captures the expected filtering contract for `?view=PORTFOLIO` so future UI refactors do not silently break operator workflows.

## Coverage Status Rules

Coverage status is resolved per `(account_id, underlying_symbol)` group:

- `Covered`: `STK_qty == abs(short_call_qty * 100)`
- `Uncovered`: `STK_qty > abs(short_call_qty * 100)`
- `Naked`: `STK_qty < abs(short_call_qty * 100)`

These rules are enforced by the backend enrichment returned from `GET /api/portfolio/holdings`.

## Filter Contract

The portfolio toolbar must support combined filtering with logical `AND` semantics:

- Coverage status: exactly one of `All`, `Covered`, `Uncovered`, or `Naked`
- Expiring options toggle: when enabled, only show rows where `dte <= DTE limit`
- Near Money toggle: when enabled, only show rows where `dist_to_strike_pct < 0.05`
- Account filter: when selected, only show rows for that `account_id`

Example:

- `Covered` + `Expiring (<6D)` + `Near Money (<5%)` + account `U110638`
- Result: only rows that satisfy all four conditions remain visible

## Reset Behavior

- `All` clears coverage status, expiring toggle, near-money toggle, and account filter
- DTE limit defaults to `6`

## Regression Coverage

Frontend filter regression tests live in:

- `frontend/src/components/portfolioFilters.test.js`

Backend coverage enrichment regression tests live in:

- `tests/test_portfolio_enrichment.py`
