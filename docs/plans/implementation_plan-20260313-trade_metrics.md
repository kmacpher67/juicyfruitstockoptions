# Implementation Plan: Trade Metrics Enhancements

## Goal Description
Enhance the Trade History dashboard to include metrics for Unrealized Profit, Unrealized Loss, and a breakdown of Total Trades into Open vs. Closed trades. This provides continuous visibility into the portfolio's unrealized performance directly within the historical trade analysis views. 

## User Review Required
- **Requirement Interpretation**: I am defining an "Open Trade" as any trade execution (Buy or Sell) that did not result in realized P&L (usually an opening transaction), and a "Closed Trade" as any execution that *did* result in realized P&L (a closing transaction). 
- **Unrealized P&L Calculation**: To avoid massive latency issues with fetching live prices for every symbol ever traded, we will fetch the live price *only* for symbols that currently have an open position (unmatched quantity in the FIFO queue). 
- Please confirm if this matches your expectation! [YES this is my expectation and logical.]

## Proposed Changes

### Backend (`app/models/__init__.py`)
- **[MODIFY] `TradeMetrics`**: 
  - Add `unrealized_profit: float = 0.0`
  - Add `unrealized_loss: float = 0.0`
  - Add `open_trades: int = 0`
  - Add `closed_trades: int = 0`
  - Define `total_trades` to be the sum of `open_trades` + `closed_trades`.

### Backend (`app/services/trade_analysis.py`)
- **[MODIFY] `calculate_pnl`**:
  - Currently returns `List[AnalyzedTrade]`. 
  - Modify to return `Tuple[List[AnalyzedTrade], Dict[str, dict]]` where the dictionary contains `{ symbol: {"qty": float, "avg_cost": float} }` representing the remaining open positions after FIFO matching.
- **[MODIFY] `calculate_metrics`**:
  - Update to accept the `open_positions` dictionary and the `analyzed_trades`.
  - Recalculate `total_trades`, `open_trades`, and `closed_trades`. 
  - (A closing trade is one where `realized_pl != 0`, an opening trade is one where `realized_pl == 0`).
  - Use `yfinance` to fetch the current price for the `open_positions` symbols to calculate `unrealized_profit` and `unrealized_loss`.

### Backend (`app/api/trades.py`)
- **[MODIFY] `get_trade_analysis`**:
  - Unpack the new tuple from `calculate_pnl`.
  - Pass `open_positions` to `calculate_metrics`.
  - Ensure the date filtering logic still works correctly.

### Backend Tests (`tests/test_trade_analysis.py`)
- **[MODIFY] `test_trade_analysis.py`**:
  - Fix the unpacking of `calculate_pnl` calls (since it will now return a tuple).

### Frontend (`frontend/src/components/TradeHistory.jsx`)
- **[MODIFY] React Component**:
  - Update the "Total Trades" `MetricCard` to show `Open: X | Closed: Y` as a subtitle or directly in the value text.
  - Add a new `MetricCard` for `Unrealized P&L` combining the Profit and Loss, or make it two separate cards. (e.g., "Unrealized P&L" showing Net, with a subset showing profit/loss).

### Documentation (`docs/learning/trade-metrics.md` & `docs/features-requirements.md`)
- **[MODIFY]**: Update definition of total trades, open trades, and closed trades. Update `features-requirements.md` checking off the task.

---

## Verification Plan

### Automated Tests
- Run `pytest tests/test_trade_analysis.py` to ensure the FIFO logic and tuple unpacking didn't break.
- Run `pytest` to ensure no other tests involving `trades.py` are broken.

### Manual Verification
- Launch the UI locally.
- Navigate to the "Trade History" view.
- Verify the new metrics "Unrealized Profit", "Unrealized Loss", and the Open/Closed trade count properly display.
- Change the time filter (1M, YTD, etc.) to ensure it recalculates dynamically.
