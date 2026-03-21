# Walkthrough: Trade History Account Metrics

I have enhanced the Trade History UI by adding a per-account metrics breakdown to the "Total Trades" card. This ensures that users can see their trading activity across the three IRA/taxable accounts at a glance.

## Key Changes

### Backend
- **Model Update**: Added `account_metrics` to the `TradeMetrics` Pydantic model in `app/models/__init__.py`.
- **Logic Isolation**: Modified `calculate_pnl` in `app/services/trade_analysis.py` to group trades by `(account_id, symbol)` instead of just `symbol`. This ensures that First-In, First-Out (FIFO) matching is isolated by account.
- **Metric Aggregation**: Updated `calculate_metrics` to compute total, open, and closed trade counts for each account and return them in the new `account_metrics` field.

### Frontend
- **UI Enhancement**: Updated `frontend/src/components/TradeHistory.jsx` to display a more detailed "Total Trades" metric card:
    - **Global Summary**: Shows total Open and Closed counts.
    - **Per-Account Breakdown**: Displays a compressed list of accounts with their specific T (Total), O (Open), and C (Closed) counts in a small font (`10px`).

## Verification Results

### Logic Verification
Manual verification confirms:
1. **P&L Isolation**: FIFO logic correctly isolated by account.
2. **Metric Accuracy**: Global and per-account counts verified.

```python
# Verification Output Snippet
ACC_A Sell P&L: 200.0 (Expected: 200.0)
ACC_B Sell P&L: 100.0 (Expected: 100.0)
Account Metrics:
  ACC_A: {'total': 2, 'open': 0, 'closed': 1}
  ACC_B: {'total': 2, 'open': 0, 'closed': 1}
```
