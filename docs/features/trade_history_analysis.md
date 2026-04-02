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
- **Dividend Rendering**: Dividend rows are shown as a distinct action/type with `source: dividend` so they are not mistaken for buy/sell executions.

## Technical Implementation
- **Source of Truth**: `ibkr_trades` collection (Ingested legacy CSVs + Live Flex Query).
- **Dividend Source**: `ibkr_dividends` (`code=RE`) is merged into `/api/trades` and `/api/trades/analysis` as normalized trade-like cash rows (`asset_class: DIV`, `buy_sell: DIVIDEND`, `source: dividend`).
- **Runtime Analysis**: P&L is calculated on-the-fly to ensure flexibility if matching logic changes (e.g., LIFO option in future).
- **API**: `/api/trades/analysis` serves the computed dataset.
