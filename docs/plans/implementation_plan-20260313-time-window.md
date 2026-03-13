# Time Window Filter for Trade History

The Trade History view and Win Rate metric currently only calculate correctly when filtering for "ALL" trades. When selecting a specific time window (like MTD, 1Y, etc.), the backend filters the raw trades from MongoDB *before* passing them to the P&L calculation (`calculate_pnl`). 

Because P&L is calculated using FIFO (matching buys with sells chronologically), filtering raw trades by date causes the calculator to ignore any opening trades made prior to the selected time window. This results in inaccurate or missing P&L data for positions closed during the window.

## Proposed Changes

### Backend API: `app/api/trades.py`
We will modify the `get_trade_analysis` endpoint so that:
1. It fetches **all** trade history for the requested symbol (or all symbols) from MongoDB without applying the `start_date` and `end_date` filters to the initial query.
2. It runs `calculate_pnl` on the full, unfiltered trade history to accurately match opening and closing trades via FIFO.
3. It filters the resulting `AnalyzedTrade` sequence *after* the P&L calculation, discarding trades that were not closed within the requested `start_date` and `end_date` window.
4. It passes only the filtered, window-specific `AnalyzedTrade` records to `calculate_metrics()`, so the Win Rate, Profit Factor, and Total P&L only reflect trades closed within the time frame.

#### [MODIFY] [trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/trades.py)
Update `get_trade_analysis` to separate database retrieval from date-window filtering.

### Frontend: `frontend/src/components/TradeHistory.jsx`
The frontend already sends `start_date` and `end_date` (e.g., `2024-01-01`). We will verify no further changes are needed to the UI date manipulation, as the layout and logic for `['ALL', 'MTD', '1M', '3M', '6M', 'YTD', '1Y']` is properly built. 

## Verification Plan

### Automated Tests
- Run `pytest tests/test_api_trades.py` checking the backend functionality for data structure integrity.
- Verify `pytest tests/test_trade_analysis.py` (if it exists) to ensure generic P&L logic isn't broken.

### Manual Verification
- Launch the application: `npm run dev` and python server.
- Navigate to `http://localhost:3000/?view=TRADES`.
- Select various time frames (e.g., `1Y`, `MTD`) and confirm:
  1. The "Win Rate" percentage recalculates reasonably.
  2. "Total P&L" changes accordingly based on the window.
  3. Opening trades constructed before the window but closed within it show the correct Realized P&L in the grid.
