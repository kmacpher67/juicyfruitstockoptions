# Implementation Plan: Pending Order Coverage

## Goal

Implement a backend-first slice of pending-order-aware portfolio coverage so Juicy Fruit can:

- capture working orders from IBKR TWS in realtime
- persist normalized open-order snapshots into Mongo
- derive pending coverage intent per `(account, underlying)` group
- expose that intent on `GET /api/portfolio/holdings`
- protect the behavior with automated tests

## Scope For This Slice

### Backend

- Extend `app/services/ibkr_tws_service.py` to capture open-order and order-status callbacks.
- Add persistence into `ibkr_orders`.
- Add a scheduler job to sync working orders from the current TWS session into Mongo.
- Derive pending-order coverage fields during portfolio holdings enrichment.

### API

- Keep the existing `GET /api/portfolio/holdings` route stable.
- Add additive fields only for pending-order intent and if-filled projection.

### Tests

- Extend TWS service tests for order callbacks and persistence.
- Extend scheduler tests for order sync.
- Extend portfolio enrichment tests for uncovered-with-pending-cover, covered-with-pending-BTC, and pending-roll inference.

## Settings / Config Review

- No new environment variables required for this slice.
- Reuse existing `IBKR_TWS_ENABLED`, host, port, and client ID settings.

## Data Model Review

### New collection

- `ibkr_orders`

### Stored shape

- raw-ish normalized order snapshot keyed by TWS identifiers such as `order_id` and `perm_id`
- explicit `source: "tws_open_order"`
- normalized account, underlying, contract, action, quantity, and status fields

### Derived API fields

- `pending_order_effect`
- `coverage_status_if_filled`
- `pending_order_count`
- `pending_cover_shares`
- `pending_buy_to_close_contracts`
- `pending_roll_contracts`

## Route / Service Review

- Keep order normalization in `ibkr_tws_service.py`
- Keep portfolio intent derivation close to portfolio holdings enrichment unless it becomes large enough to extract into a dedicated service
- Avoid breaking existing portfolio grid consumers by using additive response fields only

## Security / ACL

- No new roles
- Existing portfolio route auth remains in place

## Acceptance Criteria

1. TWS service captures working orders and order-status updates into normalized in-memory state.
2. Scheduler can persist current working orders into `ibkr_orders`.
3. `GET /api/portfolio/holdings` includes additive pending-order summary fields for matching `(account, underlying)` groups.
4. Current `coverage_status` remains based on filled positions only.
5. Regression tests cover the new order and portfolio intent behavior.

## Verification Plan

### Automated

- `pytest tests/test_ibkr_tws_service.py -q`
- `pytest tests/test_tws_scheduler_jobs.py -q`
- `pytest tests/test_portfolio_enrichment.py -q`

### Manual Follow-Up

1. Connect to local TWS.
2. Place or keep a working covered-call order open.
3. Run the order sync path.
4. Verify `ibkr_orders` receives a normalized row.
5. Verify `GET /api/portfolio/holdings` shows current coverage plus pending-order effect.

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-04-02 | **CREATED** | Planned the first backend implementation slice for pending-order-aware portfolio coverage. |
