import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.dividend_scanner import DividendScanner

@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("yfinance.Ticker")
def test_dividend_capture_analysis_logic(mock_ticker_cls, mock_mongo, mock_signal_cls, mock_opp_service):
    # Setup
    scanner = DividendScanner()
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    # 1. Mock Info (Ex-Date matches earlier scan)
    ex_date = datetime.utcnow() + timedelta(days=5)
    mock_ticker.info = {
        "currentPrice": 100.0,
        "exDividendDate": ex_date.timestamp(),
        "dividendRate": 4.0
    }
    
    # 2. Mock Option Chain
    mock_chain = MagicMock()
    mock_ticker.option_chain.return_value = mock_chain
    # Expiry 2 days after Ex-Date
    expiry = (ex_date + timedelta(days=2)).strftime("%Y-%m-%d")
    mock_ticker.options = [expiry] # Available expiries
    
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
    assert rolls[0]["current_strike"] == 100
    
    # 1. Protective (ITM -> 95 Strike)
    prot = strategies[0]
    assert prot["type"] == "Protective"
    assert prot["strike"] == 95.0
    # Net Cost = Price (100) - Premium (~6.0) = 94.0
    # Max Profit (Called) = (Strike(95) - Cost(94)) + Div(1.0) = 1 + 1 = 2.0
    # Max Return = 2.0 / 100 = 2%? No, return on risk?
    assert prot["net_cost"] < 95.0
    
    # 2. Balanced (ATM -> 100 Strike)
    bal = strategies[1]
    assert bal["type"] == "Balanced"
    assert bal["strike"] == 100.0
    
    # 3. Aggressive (OTM -> 105 Strike)
    agg = strategies[2]
    assert agg["type"] == "Aggressive"
    assert agg["strike"] == 105.0
