# Portfolio Coverage And Focus Filtering

This document captures the expected filtering contract for `?view=PORTFOLIO` so future UI refactors do not silently break operator workflows.

## Coverage Status Rules

Coverage status is resolved per `(account_id, underlying_symbol)` group:

- `Covered`: `STK_qty == abs(short_call_qty * 100)`
- `Uncovered`: `STK_qty > abs(short_call_qty * 100)`
- `Naked`: `STK_qty < abs(short_call_qty * 100)`
- `No Status` (blank): row is a flat position (`abs(quantity) == 0`) and must not be labeled `Covered`, `Uncovered`, or `Naked`

These rules are enforced by the backend enrichment returned from `GET /api/portfolio/holdings`.

## Filter Contract

The portfolio toolbar must support combined filtering with logical `AND` semantics:

- Coverage status: exactly one of `All`, `Covered`, `Uncovered`, or `Naked`
- Expiring options toggle: when enabled, only show rows where `dte <= DTE limit`
- Near Money toggle: when enabled, only show rows where `dist_to_strike_pct < near-money percent threshold`
- Account filter: when selected, only show rows for that `account_id`
- Row counter: toolbar must show the count of currently visible rows after all active filters are applied

## Underlying Stock Inclusion

When an option-focused filter is active, the result set must include the matching underlying stock row for each visible option group:

- Option-focused filters are currently `Expiring` and `Near Money`
- Visible option rows remain the primary selector
- For each matched `(account_id, underlying_symbol)` option group, include the corresponding stock row
- Do not include stock rows whose `(account_id, underlying_symbol)` group has no matched option rows

Example:

- If `Near Money` matches AMZN option rows in account `U110638`, include the `AMZN` stock row for `U110638`
- Do not include unrelated stocks such as `ERO` or `GOOG` unless their option rows also match the active option-focused filters

## Near Money Formula

For portfolio filtering, "Near Money" is the absolute percentage distance between the option strike and the underlying stock price:

- `distance_pct = abs(underlying_stock_price - option_strike) / underlying_stock_price`
- A row matches the Near Money filter when `distance_pct < selected_near_money_percent / 100`

This is intentionally absolute, not signed:

- Call slightly ITM and call slightly OTM can both be "near"
- Put slightly ITM and put slightly OTM can both be "near"

Important:

- Do not compare the option premium to the strike price
- The underlying stock price must be used as the reference value
- The grid column should be interpreted as Near Money distance, not raw option-premium distance

Example:

- `Covered` + `Expiring (<6D)` + `Near Money (<8%)` + account `U110638`
- Result: only rows that satisfy all four conditions remain visible

## Reset Behavior

- `All` clears coverage status, expiring toggle, near-money toggle, and account filter
- DTE limit defaults to `6`
- Near Money percent defaults to `8` with an allowed UI range of `0` to `20`

## Regression Coverage

Frontend filter regression tests live in:

- `frontend/src/components/portfolioFilters.test.js`

Backend coverage enrichment regression tests live in:

- `tests/test_portfolio_enrichment.py`
