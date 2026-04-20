# Implementation Plan: Juicy F-R Follow-up/Review Queue

## Goal
Implement a complete Follow-up/Review (`F-R`) workflow for reviewed trade positions in the Juicys workspace, including create/update contracts, queue filtering, and effective-entry visibility.

## Scope
- Add F-R data model contract for create/update lifecycle.
- Add F-R queue and strategy sub-filters in Juicys UI.
- Add MTM sync and review-state transitions.
- Add auditability fields and regression coverage.

## Non-Goals
- No automatic order placement.
- No tax advisory logic implementation.
- No replacement of existing Juicys scoring workflows.

## Delivery Slices

### Slice 1: Data Contract + Persistence
1. Add `juicy-fr-followup-review-001`: Create F-R item schema and validation.
2. Add `juicy-fr-followup-review-002`: Persist legs, net credit, and computed `effective_entry_price`.
3. Add `juicy-fr-followup-review-003`: Add review-state transitions (`Active`, `Reviewed`, `Assigned`).

Exit criteria:
1. API accepts and stores a valid F-R create payload.
2. API updates review-state and roll notes without data loss.

### Slice 2: Queue + UI Filtering
1. Add `juicy-fr-followup-review-004`: Juicys queue filter `status == "F-R"`.
2. Add `juicy-fr-followup-review-005`: Strategy sub-tabs (`Ratio Spreads`, `ITM Substitutions`).
3. Add `juicy-fr-followup-review-006`: Show `effective_entry_price` in list/detail views.

Exit criteria:
1. F-R records appear only when filter is active.
2. Strategy tabs partition items correctly.
3. Effective entry value renders consistently.

### Slice 3: MTM + Roll Tracking + Tests
1. Add `juicy-fr-followup-review-007`: MTM sync fields (`underlying_last_price`, `last_mtm_sync_at`).
2. Add `juicy-fr-followup-review-008`: Roll-tracking fields and short-call stance notes.
3. Add `juicy-fr-followup-review-009`: Backend and frontend regressions for F-R create/update/filter flows.

Exit criteria:
1. MTM sync updates unrealized snapshot fields safely.
2. Roll actions are auditable per item.
3. Regression tests cover happy path and invalid payloads.

## Related F-R Items (Delivery Backlog)
- `juicy-fr-followup-review-001`: F-R create payload contract. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-002`: Strategy-leg normalization (ratio spread vs ITM substitution). Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-003`: Net credit and effective-entry computation. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-004`: F-R queue filter in Juicys tab. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-005`: Strategy sub-tabs in Juicys queue. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-006`: Review-state transitions and assignment flow. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-007`: MTM sync and stale-state indicators. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-008`: Roll analysis notes and position intent tracking. Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).
- `juicy-fr-followup-review-009`: Regression tests (API + UI). Reference: [Put Ratio Spreads](../learning/put_ratio_spreads.md).

## Risks
1. Existing Juicys schema drift may cause migration mismatch.
2. Strategy-leg shape can vary across historical records.
3. MTM timestamps can become misleading without a strict freshness policy.

## Verification Plan
1. Unit tests for schema validation and `effective_entry_price` calculation.
2. API tests for create/update transitions and status filtering.
3. UI tests for Juicys filter/sub-tab behavior and rendered effective entry value.

## Related Documents
- [Master F-R](../features-requirements.md)
- [Juicy F-R Feature Contract](../features/juicy_fr_followup_review.md)
- [Juicys Navigation + Optimizer Workspace](../features/juicys_navigation_optimizer_workspace.md)
- [Put Ratio Spreads](../learning/put_ratio_spreads.md)
