import pytest
from app.models import TradeRecord
from app.services.trade_analysis import calculate_pnl, calculate_metrics

def test_calculate_pnl_simple_long():
    """Test simple Buy then Sell for profit."""
    trades = [
        TradeRecord(TradeID="1", Symbol="AAPL", Quantity=10, TradePrice=100.0, IBCommission=-1.0, DateTime="20240101"),
        TradeRecord(TradeID="2", Symbol="AAPL", Quantity=-10, TradePrice=110.0, IBCommission=-1.0, DateTime="20240102")
    ]
    
    results, open_positions = calculate_pnl(trades)
    
    assert len(results) == 2
    # Buy trade has 0 realized PL
    assert results[0].realized_pl == -1.0 # Just comm
    
    # Sell trade: (110 - 100) * 10 = 100 profit. Minus comms (-1). Total 99.
    # Logic in service subtracts abs(comm) from PL.
    # Let's check the service logic again.
    # realized_pl = (110 - 100) * 10 = 100. 
    # analyzed.realized_pl = realized_pl - abs(comm) = 100 - 1 = 99.
    assert results[1].realized_pl == 99.0

def test_calculate_pnl_fifo():
    """Test FIFO matching: Buy 10, Buy 10, Sell 15."""
    trades = [
        TradeRecord(TradeID="1", Symbol="AAPL", Quantity=10, TradePrice=100.0, DateTime="20240101"), # Batch 1
        TradeRecord(TradeID="2", Symbol="AAPL", Quantity=10, TradePrice=110.0, DateTime="20240102"), # Batch 2
        TradeRecord(TradeID="3", Symbol="AAPL", Quantity=-15, TradePrice=120.0, DateTime="20240103") # Sell 15
    ]
    # Sell 15 matches:
    # 10 from Batch 1 @ 100 (Profit: 20/share * 10 = 200)
    # 5 from Batch 2 @ 110 (Profit: 10/share * 5 = 50)
    # Total PL = 250
    
    results, open_positions = calculate_pnl(trades)
    assert results[2].realized_pl == 250.0

def test_calculate_pnl_short_roundtrip():
    """Test Short Sell then Cover."""
    trades = [
        TradeRecord(TradeID="1", Symbol="TSLA", Quantity=-10, TradePrice=200.0, DateTime="20240101"), # Short
        TradeRecord(TradeID="2", Symbol="TSLA", Quantity=10, TradePrice=180.0, DateTime="20240102")   # Cover
    ]
    # Cover matches Short:
    # (Short Price 200 - Cover Price 180) * 10 = 200 Profit
    
    results, open_positions = calculate_pnl(trades)
    assert results[1].realized_pl == 200.0

def test_calculate_metrics():
    """Test metrics aggregation."""
    trades = [
        TradeRecord(TradeID="1", Symbol="A", Quantity=10, TradePrice=100, DateTime="1"),
        TradeRecord(TradeID="2", Symbol="A", Quantity=-10, TradePrice=110, DateTime="2") # +100
    ]
    analyzed, open_positions = calculate_pnl(trades) # PL: -0, +100 (ignoring comms for simple test if defaults 0)
    
    metrics = calculate_metrics(analyzed, open_positions)
    
    assert metrics.total_pl == 100.0
    assert metrics.winning_trades == 1
    assert metrics.total_trades == 2 # 1 buy (open), 1 sell (closed)
    assert metrics.closed_trades == 1
    assert metrics.open_trades == 1
    
    assert metrics.win_rate == 100.0
    # Updated logic returns gross_win (100.0) instead of inf when no losses
    assert metrics.profit_factor == 100.0
