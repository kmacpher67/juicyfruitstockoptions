import sys
from unittest.mock import MagicMock

# 1. Mock problematic modules BEFORE importing anything else
mock_yf = MagicMock()
sys.modules["yfinance"] = mock_yf
sys.modules["nltk"] = MagicMock()
sys.modules["nltk.sentiment.vader"] = MagicMock()
sys.modules["app.services.sentiment_service"] = MagicMock()

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

# Now import the service under test
# from app.services.dividend_scanner import DividendScanner

@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("app.services.dividend_scanner.NewsService") # Mock NewsService too
def test_dividend_capture_analysis_logic(mock_news_cls, mock_mongo, mock_signal_cls, mock_opp_service):
    # Setup
    from app.services.dividend_scanner import DividendScanner
    scanner = DividendScanner()
    
    # We need to mock yfinance.Ticker usage inside the method
    # Since we mocked the module, we can configure instances from there
    mock_ticker = MagicMock()
    mock_yf.Ticker.return_value = mock_ticker

    # 1. Mock Info (Ex-Date matches earlier scan)
    ex_date = datetime.utcnow() + timedelta(days=5)
    mock_ticker.info = {
        "currentPrice": 100.0,
        "previousClose": 99.0,
        "exDividendDate": ex_date.timestamp(),
        "dividendRate": 4.0
    }
    # Mock options attribute to simulate valid expiry
    expiry = (ex_date + timedelta(days=2)).strftime("%Y-%m-%d")
    mock_ticker.options = [expiry] 
    
    # 2. Mock Option Chain (RollService.get_option_chain_data)
    # Wait, DividendScanner calls self.roll_service.get_option_chain_data
    # We need to mock that method.
    
    # Mock RollService on the instance
    mock_roll_service = MagicMock()
    scanner.roll_service = mock_roll_service
    
    mock_chain = MagicMock()
    mock_roll_service.get_option_chain_data.return_value = mock_chain
    
    # Mock Calls DataFrame
    import pandas as pd
    calls_data = {
        "strike": [95.0, 100.0, 105.0],
        "bid": [6.00, 2.00, 0.50],
        "ask": [6.20, 2.20, 0.60],
        "impliedVolatility": [0.2, 0.2, 0.2]
    }
    mock_chain.calls = pd.DataFrame(calls_data)
    
    # Mock Smart Rolls
    mock_opp_service.return_value.get_opportunities.return_value = [
        {"proposal": {"current_strike": 100, "new_strike": 105, "net_credit": 0.5}}
    ]

    # EXECUTE
    result = scanner.analyze_capture_strategy("AAPL")
    strategies = result.get("strategies", [])
    rolls = result.get("rolls", [])
    
    # VERIFY
    assert len(strategies) == 3
    assert len(rolls) == 1
    # Check rolls struct
    # Since we mocked opp_service return, it should match
    assert rolls[0]["current_strike"] == 100
    
    # 1. Protective (ITM -> 95 Strike)
    # strike 95 < 100
    prot = next((s for s in strategies if s["type"] == "Protective"), None)
    assert prot
    assert prot["strike"] == 95.0
    
    # Check calculation
    # Net Cost = Price (100) - Premium (6.00) = 94.00
    # Max Profit = (Strike(95) - NetCost(94)) + Div(1.0) = 1 + 1 = 2.0
    assert prot["net_cost"] == 94.0
    assert prot["max_profit"] == 2.0
    
    # 2. Balanced (ATM -> 100 Strike)
    bal = next((s for s in strategies if s["type"] == "Balanced"), None)
    assert bal
    assert bal["strike"] == 100.0

    # 3. Aggressive (OTM -> 105 Strike)
    agg = next((s for s in strategies if s["type"] == "Aggressive"), None)
    assert agg
    assert agg["strike"] == 105.0
