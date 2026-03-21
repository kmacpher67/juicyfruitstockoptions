# Fix TradeMetrics ValidationError

## Goal Description
Resolve the `pydantic_core._pydantic_core.ValidationError` in `TradeMetrics` which occurs when `account_metrics` contains a `None` key. This happens when an `account_id` in a trade record is `None`.

## Proposed Changes

### [app.services.trade_analysis](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/trade_analysis.py)

#### [MODIFY] [trade_analysis.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/trade_analysis.py)

- Update `calculate_pnl` to ensure the `acc` variable is always a string.
- Update `calculate_metrics` to ensure the `acc` variable is always a string when populating `account_stats` and `account_open_counts`.

## Verification Plan

### Automated Tests
- Run the reproduction test: `pytest tests/reproduce_issue.py`
- Run existing account metrics tests: `pytest tests/test_account_metrics.py`
- Run general trade analysis tests: `pytest tests/test_trade_analysis.py` (if it exists)

### Manual Verification
- Navigate to the Trade History tab in the UI and verify it loads without errors.
