# IBKR Available Data and Order Models

> **Purpose:** Document what IBKR data Juicy Fruit can reasonably use for positions, executions, dividends, and pending orders, and define the extra normalized models needed for pending-order-aware portfolio coverage.

---

## Summary

For this project:

- **TWS / IB Gateway** is the preferred source for active intraday truth such as positions, NAV, executions, and working orders.
- **Flex** remains the source of truth for end-of-day reporting, history, dividends, and backfill.
- **Pending orders** should come from TWS first. Flex can help only as optional historical support if order-related sections are available in the configured reports.

That leads to a clean rule:

- use **filled positions** for current coverage state
- use **working orders** for pending intent
- use **Flex** for historical reconciliation and audit

---

## Source Matrix

| Capability | TWS / IB Gateway | Flex | Juicy Fruit Recommendation |
|:---|:---|:---|:---|
| Current positions | Yes, intraday | Yes, snapshot / delayed | Prefer TWS intraday, keep Flex for history/backfill |
| Current NAV / account values | Yes | Indirect / historical reporting | Prefer TWS for RT, Flex for EOD |
| Current-day executions | Yes | Yes after report availability | Prefer TWS first, later reconcile with Flex |
| Active pending / open orders | Yes | Maybe only if report configuration exposes order history; not reliable as RT truth | Prefer TWS only for active pending-order workflow |
| Dividends | No practical realtime operational source for this app | Yes | Flex remains source of truth |
| Historical audit trail | Partial, session-oriented | Strong | Flex remains the authoritative history layer |

---

## TWS / IB Gateway What We Can Use

TWS is the realtime operational layer for:

- positions
- account values / NAV
- executions
- open / working orders
- order status transitions
- option contract metadata needed to map orders back to an underlying stock

For pending-order-aware coverage, the relevant callbacks and concepts are:

- open order details
- order status updates
- order identifiers such as `orderId` and `permId`
- contract fields such as symbol, local symbol, sec type, right, strike, and expiry

Practical implication:

- TWS is the only source in this repo direction that should be trusted to answer "what orders are working right now?"

---

## Flex What We Can Use

Flex remains valuable for:

- holdings snapshots
- trade history
- dividends and cash activity
- end-of-day reconciliation
- historical audit support

Flex may also expose additional sections depending on how the report is configured. If order-related rows are available, Juicy Fruit can ingest them, but they should be treated as:

- historical
- delayed
- secondary to TWS for active order management

Practical implication:

- Flex can support audit and fallback narratives
- Flex should not replace TWS for live open-order awareness

---

## Why Pending Orders Need Their Own Models

Positions and executions are not enough to explain active portfolio management.

Examples:

- uncovered shares with a call already working to cover them
- covered shares with a buy-to-close already working
- a likely roll where the close and replacement orders are both active

If Juicy Fruit stores only holdings and executions, those cases remain invisible until after a fill.

So we need explicit normalized order models, plus a derived intent model.

---

## Proposed Normalized Models

### 1. `ibkr_orders`

Use for normalized raw order snapshots from TWS and optional Flex order-history imports.

Suggested fields:

```text
source
source_as_of
account_id
order_id
perm_id
parent_id
client_id
status
action
total_quantity
filled_quantity
remaining_quantity
order_type
tif
limit_price
aux_price
symbol
underlying_symbol
sec_type
right
strike
expiry
local_symbol
conid
open_close
order_ref
is_combo
raw
```

Notes:

- `source` should distinguish `tws_open_order` from any Flex-derived history row.
- `underlying_symbol` should be normalized even when the raw order references only an option contract.
- `raw` should preserve source payload for debugging.

### 2. `portfolio_order_intent_snapshot`

Use for the derived `(account, underlying)` view that the portfolio UI reads.

Suggested fields:

```text
account_id
underlying_symbol
as_of
coverage_status
stock_shares
short_call_contracts
covered_shares_now
uncovered_shares_now
working_order_count
pending_order_effect
pending_cover_contracts
pending_cover_shares
pending_buy_to_close_contracts
pending_roll_from_contracts
pending_roll_to_contracts
coverage_status_if_filled
intent_confidence
explanation
```

### 3. Optional `ibkr_order_events`

Use only if later we need a full status-change audit trail instead of latest snapshots.

Suggested use cases:

- troubleshooting why an order disappeared from working status
- reconstructing order lifecycle
- supporting richer roll analysis later

---

## Conservative Intent Rules

Intent should be inferred conservatively.

### `covering_uncovered`

Use when:

- the account/underlying is currently `Uncovered`
- one or more working short call sell orders exist on the same underlying

### `buying_to_close`

Use when:

- the account/underlying is currently covered by a short call
- a working `BUY` order targets that short call exposure

### `rolling`

Use only when the data strongly supports a roll, such as:

- buy-to-close leg for existing short call
- replacement sell-to-open leg on same underlying/account
- combo linkage, shared order reference, or strong pairing evidence

### `unknown`

Use when:

- there are working orders
- but the intent cannot be classified safely

This is preferable to false certainty.

---

## Coverage Logic Separation

The portfolio should keep two different truths:

### Current truth

Based only on filled positions:

- `Covered`
- `Uncovered`
- `Naked`

### If-filled projection

Based on current truth plus working orders:

- `Covered | Pending Cover`
- `Covered | Pending BTC`
- `Covered | Pending Roll`
- `Uncovered | Pending Cover`

The second layer is a projection, not a replacement for the first.

---

## Recommended Implementation Order

1. Normalize TWS open / working orders into `ibkr_orders`.
2. Build `(account, underlying)` grouping logic for pending-order effect.
3. Expose the derived summary to `?view=PORTFOLIO`.
4. Add detail-drawer order facts and focus filters.
5. Add Flex order-history ingestion only if the configured Flex reports actually provide usable order rows.

---

## References

- `docs/features-requirements.md`
- `docs/features/portfolio_pending_order_coverage.md`
- `docs/features/ibkr_tws_realtime.md`
- `docs/learning/ibkr-realtime-data-integration.md`

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-04-02 | **CREATED** | Documented IBKR source availability and proposed normalized models for pending orders and coverage intent. |
