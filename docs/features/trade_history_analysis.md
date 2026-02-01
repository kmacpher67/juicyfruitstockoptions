# Trade History & Analysis Feature

## Overview
This feature provides users with a comprehensive view of their trading history, including calculated metrics that are not present in the raw broker data.

## Capabilities

### 1. FIFO P&L Calculation
The system applies **First-In-First-Out (FIFO)** logic to match Buy and Sell orders.
- **Realized P&L**: Calculated for every sell order (or buy-to-cover).
- **Cost Basis**: Tracked for open positions (though primarily used for P&L derivation here).

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

## Technical Implementation
- **Source of Truth**: `ibkr_trades` collection (Ingested legacy CSVs + Live Flex Query).
- **Runtime Analysis**: P&L is calculated on-the-fly to ensure flexibility if matching logic changes (e.g., LIFO option in future).
- **API**: `/api/trades/analysis` serves the computed dataset.
