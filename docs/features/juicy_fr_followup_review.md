# Juicy Follow-up/Review (F-R) Workflow

> **Date:** 2026-04-19  
> **Status:** Planned  
> **Parent Requirements:** `docs/features-requirements.md` (`juicy-fr-followup-review-*`)

---

## Purpose

Define the operator workflow and data contract for Follow-up/Review (`F-R`) items in the Juicys workspace so reviewed trades can be created, updated, filtered, and audited consistently.

---

## Operator Workflow

### 1. Create New F-R Item

1. Capture required identity fields:
- `ticker`
- `trade_date`
- `strategy_type` (`BULL_PUT_RATIO_SPREAD_1X2` or `DEEP_ITM_CALL_SUBSTITUTION_PMCC`)

2. Capture strategy legs:
- For put ratio spreads: `1` nearest ITM long put and `2` nearest OTM short puts.
- For deep ITM calls: `0.80+` delta long call and shorter-term OTM short call.

3. Capture economics:
- `net_credit`
- `effective_entry_price` formula: `entry_strike - net_premium`

4. Mark item for the review queue:
- `status = "F-R"`
- `review_state = "Active"`

### 2. Update Existing F-R Item

1. MTM sync:
- Refresh `underlying_last_price`.
- Recompute unrealized status fields from latest market value.

2. Roll analysis updates:
- Record short-leg roll actions (if any).
- Preserve whether position intent remains short calls.

3. Completion state:
- Move `review_state` from `Active` to `Reviewed` or `Assigned` when review is finalized.

---

## Strategy Suitability Guidelines

### Bull Put Ratio Spread (1x2)
- Use when target stock is desirable but current entry price is not.
- Goal is discounted basis via premium intake and assignment path management.

### Deep ITM Call Substitution (Zebra/PMCC)
- Use when stock-like exposure is desired with lower capital outlay.
- Goal is high-delta proxy exposure with reduced cash deployment.

### Preferred Market Context
- Underlying trend: stable uptrend or orderly consolidation.
- IV context: elevated IV preferred for short premium legs.
- DTE target for short legs: `14-30` days.

---

## UI Contract (Juicys Tab)

### Primary Filter Behavior
- Primary queue filter: `status == "F-R"`.
- Sub-tabs/quick filters:
- `Ratio Spreads`
- `ITM Substitutions`

### Display Rules
- Show `effective_entry_price` prominently, not strike alone.
- Show strategy leg summary in compact notation.
- Show review state badge: `Active`, `Reviewed`, `Assigned`.

### Data Freshness
- Track `last_mtm_sync_at` timestamp per F-R item.
- Show stale marker when MTM timestamp exceeds configured freshness threshold.

---

## Required Fields (Minimum Contract)

- `fr_id`
- `status`
- `review_state`
- `ticker`
- `trade_date`
- `strategy_type`
- `legs[]`
- `net_credit`
- `effective_entry_price`
- `underlying_last_price`
- `last_mtm_sync_at`
- `notes`
- `created_at`
- `updated_at`

---

## Related Documents

- [Master F-R](../features-requirements.md)
- [Juicys Navigation + Optimizer Workspace](juicys_navigation_optimizer_workspace.md)
- [Implementation Plan — Juicy F-R Follow-up/Review](../plans/implementation_plan-20260419-juicy-fr-followup-review.md)
