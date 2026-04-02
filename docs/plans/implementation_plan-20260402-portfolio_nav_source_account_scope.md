# Implementation Plan: Portfolio NAV Source Dates + Account-Scoped Cards

## Goal

Update `?view=PORTFOLIO` NAV cards so date/source semantics are trustworthy and account-aware:

- `1 Day` always reflects Flex close date semantics (COB date from NAV1D)
- other timeframes (`7 Day`, `30 Day`, `MTD`, `YTD`, `1 Year`) display either Flex report date/time or TWS realtime as-of timestamp based on availability/freshness
- NAV cards follow the selected Portfolio `Account` dropdown (`All` = aggregate, specific account = account-scoped)
- card layout is condensed vertically without losing key source/freshness context

---

## Current-State Findings (Docs + Tests + Code)

1. NAV cards currently use aggregated cross-account stats from `get_nav_history_stats()` with no `account_id` input.
2. `PortfolioGrid` has its own account filter state, but NAV stats are not wired to it.
3. `1 Day` currently shows subtitle `Flex close`, but date rendering is mostly tooltip-driven (`date_1d`) and not explicitly COB text in-card.
4. RT values come from latest `source: "tws"` NAV snapshot, but timeframe-specific source/date metadata is not explicitly modeled per card.
5. Existing tests cover NAV aggregation/source basics (`tests/test_nav_backend.py`, `tests/test_nav_refactor.py`, `tests/test_ibkr_nav.py`) but do not cover account-scoped `/portfolio/stats` behavior.
6. Frontend tests cover account filtering for portfolio rows (`frontend/src/components/portfolioFilters.test.js`) but not NAV card account scoping/date-label behavior.

---

## Source/Date Rules (Target)

### Rule A: `1 Day`

- Value logic remains: Flex 1D start as anchor, with RT current NAV when available.
- Date label logic: always show Flex close date from `NAV1D._report_date` as `as of COB <MM/DD>`.
- This avoids implying that `1 Day` close date itself came from TWS.

### Rule B: `7 Day`, `30 Day`, `MTD`, `YTD`, `1 Year`

- If realtime snapshot is fresh and eligible for intraday update, show `as of <last_tws_update>`.
- Otherwise show Flex report date/time for the selected timeframe.
- API should expose source/date metadata per timeframe so UI does not infer source heuristically.

### Rule C: Account Scope

- `All` account selection: aggregate across all accounts (current behavior).
- Specific account selection: all NAV cards recompute from only that account's NAV history and TWS snapshot rows.

---

## Backend Changes

### 1. `app/services/portfolio_analysis.py`

- Extend `get_latest_live_nav_snapshot(account_id: str | None = None)`:
  - optional account filter in pipeline (`account_id` match)
  - keep aggregate behavior when account is omitted.
- Extend `get_nav_history_stats(account_id: str | None = None)`:
  - apply optional account filter to `find_one` and aggregate match stages
  - return identical schema plus additive per-timeframe source/date metadata
  - preserve existing defaults for backward compatibility.

Suggested additive payload shape:

```json
{
  "timeframe_meta": {
    "1d": {"value_source": "flex_close_plus_rt_current", "end_date_source": "flex_close", "end_date": "2026-04-01"},
    "7d": {"value_source": "tws_rt_calc", "end_date_source": "tws_rt", "end_date": "2026-04-02T10:41:00-04:00"},
    "30d": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": "2026-04-01"}
  }
}
```

### 2. `app/api/routes.py`

- Update `/portfolio/stats`:
  - add optional `account_id` query param
  - normalize `ALL`/empty to aggregate mode
  - pass scoped value to `get_nav_history_stats(account_id=...)`.
- Update `/portfolio/nav/live`:
  - add optional `account_id` query param
  - pass scoped value to `get_latest_live_nav_snapshot(account_id=...)`.

### 3. Market-Open / Freshness Gate

- Add helper in backend for deciding whether a TWS snapshot is eligible to stamp timeframe end-date.
- Recommended initial rule:
  - eligible when live status is connected and `last_tws_update` within freshness window (for example <= 5 minutes).
- Keep rule configurable for later tuning.

---

## Frontend Changes

### 1. Shared Account Selection

- Lift account filter state from `PortfolioGrid` to `Dashboard` (or propagate selected account upward via callback).
- Pass selected account to:
  - `PortfolioGrid` (existing filtering)
  - `NAVStats` (new scoped stats/live fetches)
- Ensure `All` remains default.

### 2. `NAVStats.jsx` Data Fetch

- Include `account_id` in:
  - `/portfolio/stats`
  - `/portfolio/nav/live`
  - manual sync refresh path.
- Render subtitle/date using `timeframe_meta` from API.

### 3. Condensed Card Layout

- Reduce height from current `h-[74px]` to compact variant (for example `h-[60px]` to `h-[64px]`).
- Keep label/value/subtitle, but tighten vertical spacing and text sizes.
- Replace vague subtitles with concise `as of` text:
  - `1D`: `as of COB 04/01`
  - others: `as of 10:41 ET` or `as of 04/01` (based on source/date type)

---

## Test Plan

### Backend Tests

1. Extend `tests/test_nav_backend.py`:
- account-scoped `/portfolio/stats?account_id=...` returns only that account values.
- account-scoped `/portfolio/nav/live?account_id=...` returns only that account snapshot.

2. Extend `tests/test_nav_refactor.py`:
- `get_nav_history_stats(account_id=...)` aggregates correctly with mixed-account fixtures.
- timeframe metadata for `1d` remains Flex-close anchored even when RT is present.

3. Add freshness/date-source tests (new or in existing nav test files):
- when RT snapshot is fresh, non-1D timeframes can expose `end_date_source=tws_rt`.
- when RT stale/unavailable, they fall back to Flex report date source.

### Frontend Tests

1. Add/update tests in `frontend/src/components`:
- account selection drives NAV API params.
- `1 Day` subtitle renders COB close date label from API metadata.
- non-1D cards render RT vs Flex `as of` label per metadata.

2. Keep existing `portfolioFilters.test.js` behavior intact (no regressions).

---

## Rollout / Safety

1. Deploy additive API fields first (backward compatible).
2. Ship frontend account-scoped wiring and compact card UX behind existing role-gated portfolio view.
3. Validate manually with:
   - `All` account
   - one account with RT updates
   - one account with Flex-only fallback
4. Confirm no regression to current live status diagnostics.

---

## Manual Verification Checklist

1. Open `?view=PORTFOLIO`, default `All` account:
- NAV cards equal aggregate totals.

2. Select specific account from `Account` dropdown:
- NAV cards refresh to account-only values.

3. With connected TWS during market hours:
- `1 Day` shows COB date label from Flex close date.
- other ranges show RT as-of timestamp when fresh.

4. With TWS unavailable/disconnected:
- all cards show Flex fallback dates with accurate unavailable diagnostics.

5. Confirm compact layout reduces vertical space and remains readable on desktop and mobile widths.

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-04-02 | **CREATED** | Planned Portfolio NAV date/source/account-scope updates based on current docs, code, and tests. |
