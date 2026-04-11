# Trade History & Analysis Feature

## Overview
This feature provides users with a comprehensive view of their trading history, including calculated metrics that are not present in the raw broker data.

## Capabilities

### 1. FIFO P&L Calculation
The system applies **First-In-First-Out (FIFO)** logic to match Buy and Sell orders.
- **Realized P&L**: Calculated for every sell order (or buy-to-cover).
- **Cost Basis**: Tracked for open positions (though primarily used for P&L derivation here).
- **Dividend Cash Events**: Realized dividends (`code=RE`) are mapped into the trade-analysis stream as explicit `DIVIDEND` rows so cash yield appears in the same timeline as trades.

### 2. Performance Metrics
A summary dashboard provides:
- **Total P&L**: Net profit across all analyzed trades.
- **Win Rate**: Percentage of closing trades that were profitable.
- **Profit Factor**: Ratio of Gross Win / Gross Loss.
- **Total Trades**: Count of executed orders.

### 3. User Interface
- **Grid View**: Searchable, sortable table of all trades.
- **Filtering**: Filter by Symbol to see asset-specific history.
- **Visuals**: Green/Red indicators for profitable/unprofitable trades.
- **Account Context**: Metrics are grouped by `account_id` to provide per-portfolio insights. Missing account identifiers are automatically categorized as `"Unknown"`.
- **Timeframe Semantics**: `RT` means current-calendar-day live TWS executions. `1D` means the last completed trading day, so on Saturday, Sunday, and Monday it should still show Friday's completed trade activity.
- **Operator Visibility Rule**: If the selected Trade History timeframe includes an expiration outcome row and the backend payload contains `action: EXPIRED` or `action: ASSIGNED`, the grid `Action` column must show that exact source value.
- **Dividend Rendering**: Dividend rows are shown as a distinct action/type with `source: dividend` so they are not mistaken for buy/sell executions.
- **Expiration Outcome Rendering**: Option expiration outcomes should be represented explicitly as timeline events, preserving the raw broker source action names such as `EXPIRED` and `ASSIGNED` while also supporting a normalized internal outcome field for app logic.
- **Underlying Period Trace**: Operators should be able to select an underlying stock and a period, then see the related `STK` and `OPT` trade rows, per-row P&L, and aggregate totals for that underlying activity.

## Technical Implementation
- **Source of Truth**: `ibkr_trades` collection (Ingested legacy CSVs + Live Flex Query).
- **Dividend Source**: `ibkr_dividends` (`code=RE`) is merged into `/api/trades` and `/api/trades/analysis` as normalized trade-like cash rows (`asset_class: DIV`, `buy_sell: DIVIDEND`, `source: dividend`).
- **Runtime Analysis**: P&L is calculated on-the-fly to ensure flexibility if matching logic changes (e.g., LIFO option in future).
- **API**: `/api/trades/analysis` serves the computed dataset, and `/api/trades/analysis/underlying` serves an underlying-level trace for `STK` + `OPT` + dividends over a selected period.
- **Underlying Normalization**: Option contracts must carry a canonical `underlying_symbol` so long option local symbols can be grouped back to the stock for cross-asset timeline analysis.
- **Expiration Matching Rule**: Expiration outcome rows must remain linked to the original option opening lots, preserve raw source action naming, and preserve source freshness so provisional intraday observations are not confused with finalized back-office records.
- **Realtime Status Rule**: `tws_live` expiration outcome rows should be labeled as provisional realtime observations (`source_stage: provisional_realtime`, `record_status: provisional`) until reconciled against later accounting-grade history.
