# Implementation Plan - Trade History Per-Account Metrics Widget

Implement a detailed metrics widget in the Trade History UI that shows trade counts (Total, Open, Closed) globally and per account.

## User Review Required

> [!IMPORTANT]
> This change modifies the P&L calculation logic to group by `(account_id, symbol)` instead of just `symbol`. This ensures FIFO matching is performed within each account individually, which is more accurate for multi-account portfolios.

## Proposed Changes

### [Backend] Models & Services

---

#### [MODIFY] [models/__init__.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models/__init__.py)
- Update `TradeMetrics` to include `account_metrics: Dict[str, Dict[str, int]]`.

#### [MODIFY] [services/trade_analysis.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/trade_analysis.py)
- Update `calculate_pnl` to use `(account_id, symbol)` as the grouping key.
- Update `calculate_metrics` to compute counts per account for:
    - `total_trades`
    - `open_trades`
    - `closed_trades`
- Populate the `account_metrics` dictionary in the returned `TradeMetrics`.

---

### [Frontend] UI Components

#### [MODIFY] [components/TradeHistory.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TradeHistory.jsx)
- Update the "Total Trades" `MetricCard` to display the per-account breakdown.
- Use smaller font and compressed layout for the breakdown to fit within the card.
- Example display:
    ```
    Total Trades (789)
    Open: 522 | Closed: 267
    -----------------------
    U12345: T:400 O:200 C:200
    U67890: T:389 O:322 C:67
    ```

## Verification Plan

### Automated Tests
- Create `tests/test_account_metrics.py` (or update `tests/test_trade_analysis.py`) to verify:
    - FIFO is correctly isolated per account.
    - `TradeMetrics` contains the correct aggregate counts.
    - `TradeMetrics.account_metrics` contains the correct per-account counts.
- Run: `pytest tests/test_trade_analysis.py`

### Manual Verification
- Start the backend and frontend.
- Navigate to the Trade History view.
- Verify the "Total Trades" card displays the aggregate and per-account breakdown correctly.
- Check that the font size is appropriately small as requested.
