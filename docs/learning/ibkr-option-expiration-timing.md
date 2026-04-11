# Learning: IBKR Option Expiration Timing

## Question

Can IBKR TWS/API tell Juicy Fruit that an option expired worthless or was assigned in real time on expiration Friday, or is that only reliable after IBKR's reporting systems update?

## Short Answer

Not reliably as a finalized "expiration outcome" event in real time.

For Juicy Fruit, the safest rule is:

- treat **TWS / API** as the intraday operational source for live positions, executions, and account changes
- treat **Trade Confirmation Flex** as a near-term but delayed execution feed
- treat **Activity Flex / statements** as the authoritative next-day history layer for finalized expiration outcomes

Assignment timing is especially important: IBKR states that a customer may not receive notice of assignment until **one or more days** after the OCC's initial assignment to IBKR.

## Why It Matters

If the app marks an option as definitively expired worthless too early, it can misstate realized profit/loss, miss a late assignment, or hide stock delivery that appears after expiration processing.

## Details

### 1. What TWS/API is good at

The TWS API is built for live operational state:

- `reqAccountUpdates` provides the same account and portfolio information shown in the TWS Account Window, but IBKR notes that unless there is a position change, this information is updated at a fixed interval of **three minutes**.
- `reqExecutions` is limited to **current-day executions** by default, and IBKR documents that it returns executions and commission reports.

This means TWS is good for:

- live fills
- changing positions
- intraday account/P&L views

But an option expiring worthless is not a normal execution fill, so there is not a guaranteed real-time execution callback that represents "expired worthless" as a trade event.

### 2. What Flex can and cannot do intraday

IBKR documents that:

- **Activity Statement Flex Queries** update **once daily at close of business**
- users would normally retrieve the **prior day's Activity Statements at the start of the following day**
- **Trade Confirmation Flex Queries** update during the day, but are **not real-time**
- a new execution is typically available in Trade Confirmation Flex within **5 to 10 minutes**

So Flex helps with historical reconciliation, but it is not the right source for a real-time expiration decision.

### 3. What IBKR says about expiration exercise behavior

IBKR's delivery/exercise documentation says that for U.S. OCC-cleared options:

- stock options that are **$0.01 or more in the money** are automatically exercised by the OCC
- contrary exercise instructions on expiration day must be entered through the **TWS Option Exercise** window

Inference from that rule:

- if a long U.S. equity option is not in the money enough to be auto-exercised and no contrary instruction is sent, it should expire worthless
- however, the app should still wait for IBKR's post-expiration processing/history layer before calling the result final

### 4. Assignment is the biggest timing risk

IBKR's option assignment disclosure says:

- each night IBKR receives the OCC **exercise and assignment activity** file
- a customer may **not receive notice of an assignment until one or more days following** the date of the OCC's initial assignment to IBKR

This is the strongest reason not to treat same-night TWS observations as final assignment truth.

## Stable Rules

- TWS/API is the best source for intraday operational truth, not for finalized back-office expiration accounting.
- Trade Confirmation Flex is delayed and should be treated as near-term reconciliation, not real-time truth.
- Activity Flex / statements should be treated as the authoritative finalized history source for expiration outcomes.
- Assignment handling can lag and must be treated as time-sensitive and potentially delayed.

## Unstable or Time-Sensitive Assumptions

- Exact same-night posting times in TWS, Client Portal, or Flex may vary by IBKR processing and exchange/clearing workflow.
- Whether a disappearing option position appears before or after a stock delivery/assignment row can vary by source and timing.
- Any implementation that labels an expiration outcome before next-day reconciliation should show a provisional/finalized distinction.

## Impact On The Project

- Add source freshness/status to expiration-derived trade rows.
- Preserve the raw IBKR/TWS Trades window `ACTION` values exactly as observed (`EXPIRED`, `ASSIGNED`, etc.), and add a separate normalized field only when needed for internal app logic.
- Model expiration outcomes explicitly instead of assuming missing positions imply finalized worthless expiration.
- Prefer finalized P&L from next-day reconciliation, while allowing provisional same-day visibility in the UI.
- Keep assignment/exercise paths linked to resulting stock trades so the operator can trace the full outcome.
- Keep Trade History time windows explicit: `RT` is current-calendar-day live data, while `1D` is the last completed trading day and should continue to show Friday outcomes across the weekend and into Monday.

## Follow-Up Questions

- [x] Operator observation: the TWS Trades window `ACTION` column can show `EXPIRED` and `ASSIGNED` on Friday night / Saturday morning before the next Activity Flex cycle lands.
- [/] Current implementation now preserves raw execution-side action text from TWS execution ingestion into `ibkr_trades` as `action` / `raw_action`, but the exact callback-to-TWS-Trades-window mapping for `EXPIRED` and `ASSIGNED` still needs broker/API confirmation.
- [ ] Should the trade-history UI show a provisional badge for same-day expiration outcomes until the next Activity Flex run lands?

## Sources

- IBKR Campus, Flex Web Service: https://ibkrcampus.com/campus/ibkr-api-page/flex-web-service/
- Interactive Brokers, Delivery, Exercise and Corporate Actions: https://portal.interactivebrokers.com/en/trading/delivery-exercise-actions.php
- Interactive Brokers option assignment disclosure excerpt surfaced in IBKR search results: https://www.interactivebrokers.com/download/option_exercise_disclosure.pdf
- TWS API account updates reference: https://interactivebrokers.github.io/tws-api/account_updates.html
- TWS API executions reference: https://interactivebrokers.github.io/tws-api/executions_commissions.html
- TWS API client reference for `reqExecutions`: https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html

## Gemini Review Notes

The Gemini comments were useful in two ways:

- they reinforced the need for a dedicated expiration P&L feature and an underlying-level profit tracer
- they highlighted your operator observation that the TWS Trades window `ACTION` column can already show `EXPIRED` and `ASSIGNED` before the next Activity Flex cycle

After review:

- those proposed F-R items are now covered by the existing roadmap items in `docs/features-requirements.md`
- one refinement was still needed: explicitly preserve the raw source naming from IBKR/TWS instead of replacing it with app-invented labels

### What We Accept From The Gemini Notes

- The dashboard should ingest and display early TWS expiration outcome rows if they are available before next-day Flex.
- `EXPIRED` and `ASSIGNED` should remain visible exactly as delivered by the source.
- The underlying profit tracer should include stock, options, and dividend cash events over a selected period.

### What We Treat As Inference, Not Confirmed Fact

- The statement that TWS is "hooked directly into the live broadcast from the OCC" is plausible, but not verified by the IBKR sources cited above.
- The specific Friday-night timestamps and Saturday batch cadence may be operationally true in your observations, but they are not established as durable guarantees in the cited IBKR docs.

### Practical Project Rule

Use this hierarchy:

- TWS Trades / live feed: earliest visible operational outcome, preserve raw `ACTION`
- Flex / statements: finalized accounting-grade confirmation

If both exist, Juicy Fruit should keep both the raw realtime observation and the later finalized reconciliation record rather than collapsing away the source distinction.
