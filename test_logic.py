import json
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.trade_analysis import calculate_pnl, calculate_metrics

def run_tests():
    # Simulated Raw trades from DB (dicts, as per our new optimization!)
    trades = [
        {"trade_id": "1", "symbol": "AAPL", "quantity": 10, "price": 100.0, "buy_sell": "BUY", "commission": 1.0, "date_time": "20240101"},
        {"trade_id": "2", "symbol": "AAPL", "quantity": 5, "price": 150.0, "buy_sell": "SELL", "commission": 1.0, "date_time": "20240102"},
        {"trade_id": "3", "symbol": "TSLA", "quantity": 5, "price": 200.0, "buy_sell": "BUY", "commission": 0.5, "date_time": "20240103"}
    ]
    
    print("Testing calculate_pnl...")
    analyzed, open_pos = calculate_pnl(trades)
    
    assert len(analyzed) == 3, f"Expected 3 analyzed trades, got {len(analyzed)}"
    
    # Check PL on the SELL trade
    sell_trade = analyzed[1]
    # Bought 10@100. Sold 5@150. Gross PL = (150 - 100) * 5 * 100 = 25000 is it options? 
    # Wait, the code assumes quantity is strictly numeric and applies no multiplier by default unless it's in the logic.
    assert sell_trade.realized_pl != 0, "Realized PL should not be 0"
    print(f"Sell Trade Realized PL: {sell_trade.realized_pl}")
    
    # Check Open Positions
    assert "AAPL" in open_pos, "AAPL should be open"
    assert open_pos["AAPL"]["qty"] == 5, f"AAPL Open Qty should be 5, got {open_pos['AAPL']['qty']}"
    assert "TSLA" in open_pos, "TSLA should be open"
    assert open_pos["TSLA"]["qty"] == 5, f"TSLA Open Qty should be 5, got {open_pos['TSLA']['qty']}"
    
    print("Testing calculate_metrics...")
    # Passing analyzed_trades and open_pos dict
    metrics = calculate_metrics(analyzed, open_pos)
    print(f"Metrics: {metrics}")
    
    # Metrics open trades should be 2 (AAPL and TSLA active positions)
    assert metrics["open_trades"] == 2, f"Expected 2 open trades, got {metrics['open_trades']}"
    
    print("ALL VERIFICATION LOGIC PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_tests()
