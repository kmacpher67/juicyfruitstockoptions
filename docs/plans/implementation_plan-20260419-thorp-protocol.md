# Implementation Plan: Edward Thorp Protocol — Ticker Modal Audit Tab
**Date:** 2026-04-19  
**Short Name:** thorp-protocol  
**Status:** Proposed — Awaiting Approval

---

## Summary

Integrate Edward Thorp's 10-point investment evaluation framework as a new **"Thorp Audit"** tab in the existing `TickerModal.jsx`. A new `app/services/thorp_service.py` will compute the 10 framework points from data already in MongoDB (stock_data, juicy_opportunities, ibkr_holdings, trades) and expose them via a new API endpoint. The goal is to give Trader Ken a mathematically rigorous per-ticker risk/edge audit at the moment of decision.

**Reference:** [Thorp Modal Integration Feature Doc](../features/thorp_modal_integration.md) | [Kelly Criterion Options Learning Doc](../learning/kelly-criterion-options.md) | [Thorp Protocol Learning Doc](../learning/thorp-protocol-investing.md)

---

## Planning Checklist (create-a-plan.md compliance)

### 1. Settings Updates
- [ ] No new env vars required — consumes existing MongoDB data.
- [ ] No changes to `config.py` or `.env` for Phase 1.
- [ ] Inflation baseline constant (5.9%) stored in `system_config` collection as `thorp_inflation_baseline`; readable/editable from Settings UI.

### 2. ACL Security Roles
- [ ] New endpoint follows existing JWT-auth guard (same pattern as `/api/ticker/{symbol}`).
- [ ] Read-only endpoint — no write permissions introduced.

### 3. Data Model ETL and Views
- [ ] No new collections. Reads from: `stock_data`, `juicy_opportunities`, `ibkr_holdings`, `trades`.
- [ ] `thorp_service.py` computes views from these collections at query time — consistent with project pattern.
- [ ] Optional: cache last-computed Thorp result per ticker in `stock_data` under `thorp_audit` sub-key with TTL to avoid redundant recompute.

### 4. New Routes / Services / Models
- [ ] **`GET /api/thorp/{symbol}`** — returns 10-point Thorp audit payload.
- [ ] **`app/services/thorp_service.py`** — single-responsibility service, no business logic in routes.
- [ ] **`ThorpAudit` Pydantic model** in `app/models/thorp.py` — strongly typed response.

### 6. Mission Compliance
- [ ] Directly supports Trader Ken's goal: data-dense, yield-first, decision-support tooling.
- [ ] Density over fluff — tab renders a concise scoring table, not prose cards.

### 8. Best Practices
- [ ] Black-Scholes Kelly inputs already available via `greeks_calculator.py` and `juicy_opportunities`.
- [ ] Financial data fabrication rule: if required inputs are missing, return `status: "INSUFFICIENT_DATA"` per point — never invent numbers.
- [ ] OWASP: symbol param sanitized via existing pattern (alphanumeric + `./-`).

---

## Implementation Phases

### Phase 1 — Backend Service + API (stock-analysis-thorpe-001 to 004)
Estimated scope: 1 session.

**Files:**
- `app/models/thorp.py` — Pydantic models for request/response
- `app/services/thorp_service.py` — 10-point computation engine
- `app/api/routes.py` — add `GET /api/thorp/{symbol}` endpoint (append, do not break existing routes)
- `tests/test_thorp_service.py` — unit + integration tests

**Point-by-point data sources:**

| Point | ID | Data Source | Formula / Logic |
|---|---|---|---|
| Edge Audit | thorpe-003 | `juicy_opportunities.score`, `juicy_opportunities.win_rate_hist`, `system_config.thorp_inflation_baseline` | `edge = win_rate * avg_yield - (1-win_rate) * avg_loss`; compare to baseline |
| Position Sizing (Kelly) | thorpe-004 | `juicy_opportunities.yield_pct`, `juicy_opportunities.win_rate_hist`, `ibkr_holdings` current position size | `f* = (b*p - q) / b`; half-Kelly = `f*/2`; show current vs recommended |
| Inefficiency Map | thorpe-005 | `stock_data.call_put_skew`, `stock_data.iv_vs_rv` (if computed) | Flag skew > 1.5 or IV/RV gap > 20% as anomaly |
| Ruin Check | thorpe-006 | `ibkr_holdings.market_value`, `ibkr_holdings.position`, `ibkr_holdings.avg_cost` | Simulate -25% drop on current position; compute NLV impact |
| Fraud Scan | thorpe-007 | `juicy_opportunities.volume`, `stock_data.avg_volume` | Flag if option volume > 3x avg or premium > theoretical BS value by >30% |
| Compounding Review | thorpe-008 | `trades` (win rate, hold days, realized PnL), `juicy_opportunities.annualized_yield_pct` | Compare realized annualized return vs linear growth model |
| Adaptability Check | thorpe-009 | `trades` last 3-4 occurrences of ticker/strategy combo | Compute yield trend slope; flag if declining >15% per cycle |
| Independence Test | thorpe-010 | `stock_data.news_sentiment`, `stock_data.markov_prediction` | Flag "crowded consensus" when sentiment and price signal agree with >80% community bias |
| Circle of Competence | thorpe-011 | `trades` filtered by `asset_class` + `strategy` | Win rate for this ticker's asset/strategy category from trade history |
| Thorp Decision | thorpe-012 | Aggregate score from all 9 above points | Top 3 ranked actions with edge/risk/first-step |

### Phase 2 — Frontend Tab UI (stock-analysis-thorpe-001 frontend)
Estimated scope: 1 session.

**Files:**
- `frontend/src/components/TickerModal.jsx` — add "Thorp Audit" as 7th tab
- `frontend/src/utils/thorpHelpers.js` — shared formatting / score rendering helpers
- `frontend/tests/specs/modal.spec.js` — extend with Thorp tab assertions

**UI Rules (Density over Fluff):**
- Tab label: `Thorp Audit`
- Layout: single scrollable table — one row per Thorp point
- Columns: `#`, `Framework Point`, `Status` (✓ Edge / ⚠ Caution / ✗ Risk), `Score/Value`, `Detail`
- `Thorp Decision` section pinned to bottom: top 3 moves in a separate summary card
- Colors: green = edge confirmed, yellow = caution, red = ruin risk
- Loading/error states follow existing `TabErrorBadge` pattern from `tickerModalResilience.js`

### Phase 3 — Learning Docs & F-R Linkage
**Files:**
- `docs/learning/thorp-protocol-investing.md` — Thorp framework math reference
- `docs/learning/kelly-criterion-options.md` — Kelly formula for options traders
- `docs/features/thorp_modal_integration.md` — UI/UX spec + data binding
- `docs/features-requirements.md` — mark items `[/]` when starting, `[x]` when done

---

## Definition of Done

- [ ] `pytest` passes including `tests/test_thorp_service.py`
- [ ] Frontend Playwright modal spec covers Thorp tab loading + error states
- [ ] All 10 points render in dark-theme modal tab
- [ ] `INSUFFICIENT_DATA` gracefully rendered (no fabricated numbers)
- [ ] F-R items `thorpe-001` through `thorpe-012` marked `[x]`
- [ ] Feature doc + learning docs linked from F-R
- [ ] No new env vars required for Phase 1

---

## Open Questions

1. **Win Rate Source**: `juicy_opportunities` does not currently store historical win rates per ticker. Phase 1 should compute from `trades` collection. Should we add `win_rate_hist` to `juicy_opportunities` as a persisted field? Recommend: yes, compute on scanner run.
2. **IV vs RV Gap**: `stock_data` does not currently store realized volatility. Needed for `thorpe-005`. Phase 1 can skip IV/RV and flag as `PENDING_DATA` pending ATR-based approximation.
3. **Kelly Denominator `b`**: For covered calls `b = premium_received / (strike - premium)`. For long stock `b = target_price / entry - 1`. Confirm formula variant per strategy type before coding.

---

## Risk & Dependencies

- No breaking changes to existing endpoints — new route appended.
- Depends on `juicy_opportunities` having `yield_pct`, `win_rate_hist`, and `annualized_yield_pct` populated. If sparse, service returns `INSUFFICIENT_DATA` per point.
- Phase 2 frontend adds tab 7 to TickerModal — existing tabs unaffected.

---

> **PAUSE: User approval required before execution.**
