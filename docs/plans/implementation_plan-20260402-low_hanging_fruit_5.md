# Implementation Plan: Low-Hanging Fruit Batch — 5 Items
**Date:** 2026-04-02
**Author:** Claude Code

## Scope
Five narrowly-scoped, bounded items from the F-R backlog:
1. `events-stk-filter-bug` — OPT symbols slip to yfinance in corporate events scanner
2. `ibkr-tws-ui-nav-compact-001` — Reduce NAV card vertical footprint
3. `portfolio-coverage-001..004` — Coverage status regression tests
4. `portfolio-export-004` — CSV export filter regression tests (JS)
5. `Stock Analysis — Ticker Quick Links` — Add G/Y links to StockGrid `?view=ANALYSIS`

---

## 1. events-stk-filter-bug

**Problem:** `generate_corporate_events_calendar()` builds a `symbols` list through manual
`secType` / OCC-string checks but does NOT call `_normalize_to_stk_symbol()` as a final
guard. When a holding's `secType` field is absent or has a different capitalisation (e.g. from
TWS live data), the raw OCC string `AMD   260220C00235000` passes through and causes
`yfinance` HTTP 404 errors.

**Fix:** After the existing symbol-building loop (line ~395 in `dividend_scanner.py`), add a
post-processing step that pipes every element through `_normalize_to_stk_symbol()` and
drops `None` results, then deduplicates.

**Files changed:**
- `app/services/dividend_scanner.py` — post-process `symbols` list
- `tests/test_corporate_events.py` — add two regression cases:
  - OPT symbol is excluded from yfinance calls
  - Underlying STK root symbol IS kept when it resolves

---

## 2. ibkr-tws-ui-nav-compact-001

**Problem:** Each `StatCard` and the Sync All button use `h-[62px]`, and the value font is
`text-sm lg:text-base`. Combined the NAV row consumes excessive vertical space.

**Fix:** In `NAVStats.jsx`:
- `StatCard`: `h-[62px]` → `h-[52px]`, font `text-sm lg:text-base` → `text-xs lg:text-sm`,
  subtitle margin `mt-0.5` → `mt-0`, label uppercase `text-[10px]` → `text-[9px]`.
- Sync All button: `h-[62px]` → `h-[52px]`, NAV value font `text-base lg:text-lg` →
  `text-sm lg:text-base`, status/freshness `text-[10px]` → `text-[9px]`.

No test changes — visual only, existing `navStatsUtils.test.js` still covers logic.

---

## 3. portfolio-coverage-001..004

**Problem:** The coverage-status logic (`_resolve_coverage_status`, `_is_short_call_position`)
in `app/api/routes.py` is correct but has zero unit-test coverage, leaving it prone to silent
regression.

**Fix:** Create `tests/test_coverage_status.py` exercising:
- `_resolve_coverage_status`: Covered / Uncovered / Naked / flat-position edge cases
- AMD scenario: 200 STK shares, -2 CALL contracts → "Covered"
- `_is_short_call_position`: CALL OPT (short), PUT OPT (short), long CALL, STK — all
  branches
- Flat position row (`qty == 0`) gets blank `coverage_status` via `_is_flat_position_row`

---

## 4. portfolio-export-004

**Problem:** `applyPortfolioFilters` in `portfolioFilters.js` has no regression tests; a
shape change in filter logic could silently break the CSV export which depends on it.

**Fix:** Create `frontend/src/components/portfolioFilters.test.js` (Node.js native test runner)
covering:
- `rowMatchesPortfolioFilters`: account, coverage, expiring, near-money, pending-effect,
  showStocks combinations
- `applyPortfolioFilters`: STK inclusion when `showStocks=true` + option-focused filters,
  STK suppression when `showStocks=false`

---

## 5. Stock Analysis — Ticker Quick Links

**Problem:** `StockGrid.jsx` `LinkRenderer` opens a modal on ticker click but provides no
direct G (Google Finance) / Y (Yahoo Finance) quick links. They exist on `?view=PORTFOLIO`
and `?view=TRADES` but not `?view=ANALYSIS`.

**Fix:** Update `LinkRenderer` in `StockGrid.jsx` to match the PortfolioGrid pattern:
ticker text opens modal, plus `G` / `Y` icon links at reduced opacity.

---

## Checklist
- [ ] No new env vars required
- [ ] No DB schema changes
- [ ] No new API routes
- [ ] Additive changes only (no breaking changes)
- [ ] Tests written for every change (backend pytest + frontend node:test)
- [ ] F-R items marked `[x]` when done
