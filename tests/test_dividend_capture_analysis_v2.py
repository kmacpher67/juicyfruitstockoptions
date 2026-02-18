import sys
from unittest.mock import MagicMock

# AGGRESSIVE MOCKING
sys.modules["yfinance"] = MagicMock()
sys.modules["nltk"] = MagicMock()
sys.modules["nltk.sentiment.vader"] = MagicMock()
sys.modules["py_vollib_vectorized"] = MagicMock()
sys.modules["pykalman"] = MagicMock()
sys.modules["markovify"] = MagicMock()
sys.modules["pymongo"] = MagicMock()
sys.modules["requests"] = MagicMock()

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

# Import target
from app.services.dividend_scanner import DividendScanner

@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.RollService") # Mock RollService entirely
@patch("app.services.dividend_scanner.NewsService")
def test_dividend_capture_analysis_logic_v2(mock_news, mock_roll, mock_signal, mock_opp):
    # Setup
    scanner = DividendScanner()
    
    # Mock yfinance ticker
    mock_ticker = MagicMock()
    sys.modules["yfinance"].Ticker.return_value = mock_ticker

    # 1. Mock Info
    ex_date = datetime.utcnow() + timedelta(days=5)
    mock_ticker.info = {
        "currentPrice": 100.0,
        "previousClose": 99.0,
        "exDividendDate": ex_date.timestamp(),
        "dividendRate": 4.0
    }
    mock_ticker.options = [(ex_date + timedelta(days=2)).strftime("%Y-%m-%d")]
    
    # 2. Mock Option Chain from RollService
    mock_chain = MagicMock()
    scanner.roll_service.get_option_chain_data.return_value = mock_chain
    
    import pandas as pd
    calls_data = {
        "strike": [95.0, 100.0, 105.0],
        "bid": [6.00, 2.00, 0.50],
        "ask": [6.20, 2.20, 0.60],
        "impliedVolatility": [0.2, 0.2, 0.2]
    }
    mock_chain.calls = pd.DataFrame(calls_data)
    
    # 3. Mock Smart Rolls
    scanner.opp_service.get_opportunities.return_value = []

    # EXECUTE
    result = scanner.analyze_capture_strategy("AAPL")
    strategies = result.get("strategies", [])
    
    # VERIFY
    assert len(strategies) == 3
