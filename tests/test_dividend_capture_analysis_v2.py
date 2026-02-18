"""Test Dividend Capture Analysis V2 — uses @patch decorators only (no sys.modules)."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone


@patch("app.services.dividend_scanner.NewsService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.RollService")
@patch("app.services.dividend_scanner.yf")
def test_dividend_capture_analysis_logic_v2(mock_yf, mock_roll_cls, mock_opp_cls, mock_signal_cls, mock_mongo, mock_news):
    from app.services.dividend_scanner import DividendScanner
    # Setup
    scanner = DividendScanner()

    # Configure MongoClient mock so find_one/find don't produce infinite iteration
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_db.ibkr_holdings.find_one.return_value = None  # No holdings
    mock_db.ibkr_holdings.find.return_value = []

    # Mock yfinance ticker
    mock_ticker = MagicMock()
    mock_yf.Ticker.return_value = mock_ticker

    # 1. Mock Info
    ex_date = datetime.now(timezone.utc) + timedelta(days=5)
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

