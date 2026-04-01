# Portfolio TWS Live Grid Regressions (2026-03-31)

## Purpose

Track the `?view=PORTFOLIO` rendering issues observed after the TWS realtime integration so the next implementation pass fixes the data contract and the UI together.

This is intentionally separate from handshake/trust troubleshooting. The backend may be connected and still feed a row shape that the portfolio grid does not render correctly.

## Trigger / Context

Observed on 2026-03-31 in the `My Portfolio` view while rendering a live portfolio report.

Visible symptoms from the screenshot and user notes:

- `Price` renders as `$undefined`
- `Value` renders as `$undefined`
- `Basis` renders as `$undefined`
- `Unrealized PnL` renders as `$undefined`
- `% NAV` renders as `NaN%`
- option rows are missing the full contract description
- `Type` behavior for `STK` vs `OPT` is not reliable

## Why This Matters

These are not cosmetic issues only:

- `undefined` and `NaN%` break operator trust in the portfolio view
- broken `Type` classification affects links, filters, and downstream actions
- missing option descriptions make it difficult to identify the actual contract being managed
- the failures suggest the frontend row mapper is not using a stable merged schema across Flex and TWS-backed holdings

## Prior Related Work

This bug cluster overlaps older portfolio UI work and should reference it instead of duplicating history:

- `docs/plans/walkthrough-smart_roll_markov.md` documented an earlier fix where the portfolio `Type` column fell back to `secType` or inferred `OPT` / `STK`
- `docs/features-requirements.md` already tracks portfolio filters and prior Type-column issues
- `docs/features/ibkr_tws_realtime.md` tracks live-state and runtime diagnostics, but not this grid-level data-contract regression

## FR Breakdown

- `portfolio-live-grid-001`: Prevent literal `undefined` values in currency columns.
  The portfolio row formatter must coalesce missing live fields into explicit null/fallback display states before currency formatting.
- `portfolio-live-grid-002`: Prevent `NaN%` in `% NAV`.
  Percentage calculations must short-circuit when numerator or denominator is missing, null, or zero.
- `portfolio-live-grid-003`: Restore reliable `STK` vs `OPT` typing.
  The grid must consistently resolve security type from normalized fields such as `secType`, `sec_type`, `asset_class`, or equivalent merged-source contract metadata.
- `portfolio-live-grid-004`: Restore option description rendering.
  Option rows should show a meaningful contract label including underlying, expiry, strike, and put/call when available.
- `portfolio-live-grid-005`: Normalize the merged portfolio row schema before rendering.
  Flex/EOD and TWS/live rows should expose the same canonical names for price, value, basis, unrealized PnL, `% NAV`, security type, and description.
- `portfolio-live-grid-006`: Deduplicate merged-source portfolio rows.
  Status: completed 2026-03-31. The backend now merges latest Flex/EOD and TWS/live rows by canonical portfolio key so the UI renders one visible row with deterministic source precedence instead of showing duplicates.
- `portfolio-live-grid-007`: Add regression coverage.
  Tests should cover live-only, Flex-only, and merged-source rows so older Type fallback behavior does not regress when realtime data is present.

## Acceptance Criteria

- No visible `undefined` literals in the portfolio grid
- No visible `NaN%` in `% NAV`
- `Type` column correctly distinguishes `Stock` vs `Option` for the same rows shown in the screenshot
- option rows display enough contract detail to identify the contract without opening another screen
- the same portfolio item does not render twice when both Flex and TWS data exist for it
- filters and Type-driven actions continue to work with the normalized fields
- regression tests cover the mixed-source row mapping path

## Suggested Debug Order

1. Inspect the API payload or frontend row-mapping layer for canonical field names.
2. Compare a Flex-backed row versus a TWS-backed row for price, market value, basis, unrealized PnL, security type, and description.
3. Normalize the row schema before table rendering.
4. Only after normalization, re-check formatting helpers for currency and percent columns.
5. Add regression tests for the row-mapping contract.
