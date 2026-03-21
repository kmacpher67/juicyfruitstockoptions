import pytest
from app.models import TradeRecord
from app.services.trade_analysis import calculate_pnl, calculate_metrics

def test_pnl_isolation_by_account():
    """Verify that FIFO is isolated by account_id."""
    trades = [
        # Account A: Buy 10 AAPL @ 100
        TradeRecord(TradeID="1", Symbol="AAPL", AccountId="ACC_A", Quantity=10, TradePrice=100.0, DateTime="20240101"),
        # Account B: Buy 10 AAPL @ 110
        TradeRecord(TradeID="2", Symbol="AAPL", AccountId="ACC_B", Quantity=10, TradePrice=110.0, DateTime="20240102"),
        # Account A: Sell 10 AAPL @ 120 (Should match ACC_A @ 100)
        TradeRecord(TradeID="3", Symbol="AAPL", AccountId="ACC_A", Quantity=-10, TradePrice=120.0, DateTime="20240103"),
        # Account B: Sell 10 AAPL @ 120 (Should match ACC_B @ 110)
        TradeRecord(TradeID="4", Symbol="AAPL", AccountId="ACC_B", Quantity=-10, TradePrice=120.0, DateTime="20240104")
    ]
    
    analyzed, open_positions = calculate_pnl(trades)
    
    # ACC_A profit: (120 - 100) * 10 = 200
    # ACC_B profit: (120 - 110) * 10 = 100
    
    # Find the sell trades in analyzed results
    acc_a_sell = next(t for t in analyzed if t.trade_id == "3")
    acc_b_sell = next(t for t in analyzed if t.trade_id == "4")
    
    assert acc_a_sell.realized_pl == 200.0
    assert acc_b_sell.realized_pl == 100.0
    assert len(open_positions) == 0

def test_account_metrics_counts():
    """Verify trade counts per account in metrics."""
    trades = [
        # Account A: 1 closed trade (2 legs)
        TradeRecord(TradeID="1", Symbol="A", AccountId="ACC_A", Quantity=10, TradePrice=100, DateTime="1"),
        TradeRecord(TradeID="2", Symbol="A", AccountId="ACC_A", Quantity=-10, TradePrice=110, DateTime="2"),
        # Account B: 1 open trade (1 leg)
        TradeRecord(TradeID="3", Symbol="B", AccountId="ACC_B", Quantity=5, TradePrice=50, DateTime="3")
    ]
    
    analyzed, open_positions = calculate_pnl(trades)
    metrics = calculate_metrics(analyzed, open_positions, current_prices={"B": 55.0})
    
    assert metrics.total_trades == 3
    assert metrics.open_trades == 1 # ACC_B: B
    assert metrics.closed_trades == 1 # ACC_A: A
    
    assert "ACC_A" in metrics.account_metrics
    assert metrics.account_metrics["ACC_A"]["total"] == 2
    assert metrics.account_metrics["ACC_A"]["open"] == 0
    assert metrics.account_metrics["ACC_A"]["closed"] == 1
    
    assert "ACC_B" in metrics.account_metrics
    assert metrics.account_metrics["ACC_B"]["total"] == 1
    assert metrics.account_metrics["ACC_B"]["open"] == 1
    assert metrics.account_metrics["ACC_B"]["closed"] == 0
