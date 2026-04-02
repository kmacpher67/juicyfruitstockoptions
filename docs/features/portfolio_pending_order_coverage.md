# Portfolio Pending Order Coverage

> **Date:** 2026-04-02
> **Status:** Requirements Definition
> **Primary FR Area:** `docs/features-requirements.md` -> `Portfolio` and `IBKR Pending Orders`

---

## Purpose

Define how Juicy Fruit should represent pending IBKR orders alongside current positions so Trader Ken can quickly see:

- what is covered, uncovered, or naked right now
- whether there is already a working order intended to fill uncovered shares
- whether a covered-call position has a pending buy-to-close
- whether a covered-call position appears to be rolling

The key rule is simple:

- current positions define the current truth
- pending orders define a separate "if filled" or "intent" layer

Execution history (including RT trade fills) is supporting context, but must not replace the current position snapshot used for `coverage_status`.

Pending orders should enrich the portfolio view, not rewrite filled-position reality.

---

## Problem Statement

Today the portfolio coverage logic is driven by filled stock and option positions. That answers "what is covered now?" but not "is there already an order working to fix or change this?"

Examples that need first-class visibility:

1. `300` shares of stock are `Uncovered`, but there is a pending `SELL` call order for `-3` contracts that would fully cover the shares if filled.
2. `100` shares plus `-1` short call are currently `Covered`, but there is a pending `BUY` order to close that short call. If it fills, the position becomes uncovered unless another short call replaces it.
3. `100` shares plus `-1` short call are currently `Covered`, and there is a pending buy-to-close plus a new sell-to-open call. That is likely a roll and should read differently from a plain buy-to-close.

Without that distinction, the operator sees only the current static state and misses important active management already in flight.

---

## Source Priority

### Preferred realtime source

Use **IBKR TWS / IB Gateway realtime order callbacks** as the authoritative source for active pending orders.

Reason:

- TWS can stream working order state and status changes during the trading day.
- Open / working orders are operational data, not just historical activity.

### Optional historical / backfill source

Use **Flex** only if the configured Flex queries expose order-related rows. Treat those rows as:

- historical context
- audit trail
- backfill when TWS is unavailable

Do **not** treat Flex as the primary truth for active pending orders unless the specific report proves it is fresh enough for that use, which is unlikely for intraday workflow.

---

## Required UI Concepts

Each `(account, underlying)` group should expose both of these:

### 1. Current Coverage State

Derived from filled positions only:

- `Covered`
- `Uncovered`
- `Naked`
- blank/no-status for flat rows where position quantity is `0` (do not classify these rows as covered/uncovered/naked)

### 2. Pending Order Effect

Derived from active working orders:

- `none`
- `covering_uncovered`
- `buying_to_close`
- `rolling`
- `increasing_naked_risk`
- `unknown`

The UI should show both at once, for example:

- `Uncovered | Pending Cover`
- `Covered | Pending BTC`
- `Covered | Pending Roll`

---

## Minimum Inference Rules

Inference must be conservative. If order intent is ambiguous, show facts and mark intent `unknown`.

### Covering Uncovered Shares

Likely when:

- current group is `Uncovered`
- a working order exists to `SELL` call contracts on the same underlying/account
- order quantity, right, expiry, and strike map to a call option

Derived values:

- `uncovered_shares_now`
- `pending_cover_shares`
- `uncovered_shares_if_filled`

### Buy To Close

Likely when:

- current group includes an existing short call
- a working `BUY` order targets that short call contract or a matching replacement key

This should be surfaced even if no replacement sell order exists.

### Roll

Likely when:

- there is a pending buy-to-close for an existing short call
- and there is a related pending sell-to-open call on the same underlying/account
- and the orders are linked by combo structure, parent-child relation, shared reference, or close timing strong enough to justify the inference

If the evidence is weak, show separate pending legs and keep `pending_order_effect = unknown`.

---

## Proposed Data Models

### `ibkr_orders`

Raw-ish normalized order snapshot store.

Suggested fields:

```text
source
captured_at
account_id
order_id
perm_id
parent_id
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
source_payload
```

### `portfolio_order_intent_snapshot`

Derived per `(account, underlying)` group.

Suggested fields:

```text
account_id
underlying_symbol
as_of
coverage_status
covered_shares_now
uncovered_shares_now
short_call_contracts_now
working_order_count
pending_order_effect
pending_cover_contracts
pending_cover_shares
pending_buy_to_close_contracts
pending_roll_from_contracts
pending_roll_to_contracts
coverage_status_if_filled
intent_confidence
notes
```

The UI can read from this derived view instead of reproducing inference logic client-side.

---

## UX Expectations

In `?view=PORTFOLIO`:

- show badges or columns for current coverage and pending-order effect
- show the same group-level status on the stock row and related option rows
- allow focus filters for `Pending Cover`, `Pending BTC`, and `Pending Roll`
- keep detail-level order facts available in the drawer or hover detail

In `?view=ORDERS`:

- show a dedicated open-orders table with sortable columns
- include account, order symbol, action, status, remaining quantity, order type, prices, source, and last update
- enrich each row with relevant ticker context from tracked market data (LAST, `%1D`, skew, trend fields)
- include a manual `Refresh Orders` button for immediate operator pull
- auto-refresh orders in the background while `?view=ORDERS` is active
- show a feed freshness badge using `last_order_update` and mark stale state explicitly
- include quick links on ticker cells:
  - `D` = open internal stock analysis detail
  - `G` = open Google Finance
  - `Y` = open Yahoo Options
- when the order is an option contract, use the underlying stock ticker for D/G/Y links

### BAG / Combo Orders (Current vs Target)

Current behavior:

- BAG rows are shown as top-level combo parents when present in `ibkr_orders`.
- Juicy Fruit currently does **not** provide leg drill-down from BAG rows in the Orders table.
- Practically, this can look like "orphans" when users expect to click and see the exact roll legs.

Target behavior:

- BAG rows should be expandable (or paired with grouped child rows) to show individual legs.
- UI should retain both:
  - net combo context (single BAG row with net limit/debit/credit)
  - per-leg context (BUY/SELL legs, strikes, expiry, ratio, and status)
- Add explicit BAG-parent visibility toggles so operators can choose net view vs decomposed-leg view.

In a detail drawer:

- list the exact working orders affecting the group
- show remaining quantity, price, status, and last update
- explain the derived effect in plain language

Example:

`300 shares uncovered now; 3 short call contracts working; if filled -> Covered`

---

## Acceptance Criteria

1. Current coverage state remains based only on actual filled positions.
2. Pending orders are visible separately and never silently overwrite current coverage truth.
3. Uncovered stock with a working short-call sell order is visibly different from uncovered stock with no working order.
4. Covered stock with a pending buy-to-close is visibly different from covered stock with no pending order.
5. Roll intent is shown only when evidence is strong enough; otherwise the UI falls back to separate pending-leg facts.
6. The same `(account, underlying)` pending-order summary is consistent across the stock row, option rows, and detail drawer.
7. `?view=ORDERS` uses the same dashboard role access pattern as portfolio/trades controls (`admin` and `portfolio`).
8. `?view=ORDERS` surfaces active open orders from `ibkr_orders` (`source: tws_open_order`) and clearly labels data source for each row.
9. `?view=ORDERS` provides both manual refresh and background refresh, and visibly indicates when order data is stale.

---

## Flex Orders Work Items

Current state:

- TWS open-order ingest is active and persisted.
- Flex order-history ingest is still stubbed until a concrete Flex Orders report format is available for this account.
- TWS reconciliation now marks stale open-order docs as `Inactive` after a completed open-order snapshot so leftover combo/BAG parent remnants no longer appear as active pending orders.

Required follow-ups:

1. Create IBKR Flex report/query for order history and capture its Query ID.
2. Add/update the Query ID in **Settings -> IBKR Integration -> Orders Query ID**.
3. Implement/verify parser mapping from that report into `ibkr_orders` with `source: flex_order_history`.
4. Add parser regression tests with representative Flex order rows.
5. Implement BAG leg decomposition and BAG-parent visibility controls (see F-R `ibkr-orders-012`, `ibkr-orders-013`).

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-04-02 | **CREATED** | Defined pending-order-aware coverage requirements for portfolio holdings and working-order visibility. |
| 2026-04-02 | **UPDATED** | Clarified that coverage truth must come from contract-level position snapshots; RT execution rows are context only and should not be used as direct coverage state. |
| 2026-04-02 | **UPDATED** | Clarified flat-row handling: rows with `quantity == 0` are intentionally left without a coverage label so they do not appear in Covered/Uncovered/Naked focus filters. |
| 2026-04-02 | **UPDATED** | Added `?view=ORDERS` requirements, D/G/Y linking expectations, and explicit Flex Orders report setup follow-up items. |
| 2026-04-02 | **UPDATED** | Added Orders view freshness UX requirements (manual refresh, auto-refresh, and stale indicator). |
| 2026-04-02 | **UPDATED** | Captured BAG/combo current limitation (no leg drill-down yet), target decomposition UX, and follow-up F-R links for BAG handling. |
