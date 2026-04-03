import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.dividend_scanner import DividendScanner

@patch("app.services.opportunity_service.MongoClient")
@patch("app.services.roll_service.SignalService")
@patch("app.services.roll_service.OpportunityService")
@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("app.services.dividend_scanner.yf.Ticker")
def test_dividend_feed_data_structure(mock_ticker_cls, mock_mongo, mock_signal_cls, mock_opp_service, mock_roll_opp_service, mock_roll_signal_service, mock_mongo_opp):
    # Setup
    scanner = DividendScanner()
    
    # Mock Mongo Holdings
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "123"}
    # Mock finding one holding for AAPL
    mock_db.ibkr_holdings.find.return_value = [
        {"symbol": "AAPL", "account_id": "U12345", "quantity": 100}
    ]
    
    # Mock Signal Service
    mock_signal = scanner.signal_service # Since we mocked the class, the instance in init is a mock
    # Wait, we mocked the CLASS in the decorator, so scanner.signal_service (init'd in scanner) 
    # will be an instance of the Mock class if patch was active during init?
    # Actually, we construct Scanner inside the test function, so patches are active.
    # scanner.signal_service is the Mock instance.
    scanner.signal_service.predict_future_price.return_value = {
        "predicted_price": 155.00,
        "min_sim": 150.00,
        "max_sim": 160.00
    }
    
    # Mock YFinance
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    
    # Mock Info
    ex_date = datetime.utcnow() + timedelta(days=5)
    mock_ticker.info = {
        "exDividendDate": ex_date.timestamp(),
        "dividendRate": 4.0,
        "currentPrice": 150.0,
        "targetMeanPrice": 170.0
    }
    
    # EXECUTE
    results = scanner.scan_dividend_capture_opportunities(["AAPL"])
    
    # VERIFY
    assert len(results) == 1
    opp = results[0]
    
    # Check Standard Fields
    assert opp["symbol"] == "AAPL"
    assert opp["current_price"] == 150.0
    
    # Check New Fields
    assert opp["predicted_price"] == 155.00
    assert opp["analyst_target"] == 170.0
    assert "U12345: 100" in opp["accounts_held"]
    expected_return_pct = round((((155.00 - 150.0) + (4.0 / 4)) / 150.0) * 100, 2)
    assert opp["return_pct"] == expected_return_pct
    
    # Verify Calls
    scanner.signal_service.predict_future_price.assert_called_with("AAPL", days_ahead=opp["days_to_ex"], current_price=150.0)
