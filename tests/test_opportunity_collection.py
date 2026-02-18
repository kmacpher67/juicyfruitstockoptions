import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.models.opportunity import JuicyOpportunity, OpportunityStatus
from app.services.opportunity_service import OpportunityService
from app.services.dividend_scanner import DividendScanner

# 1. Test Model
def test_juicy_opportunity_model():
    opp = JuicyOpportunity(
        symbol="AAPL",
        trigger_source="Test",
        status=OpportunityStatus.DETECTED,
        context={"price": 150.0},
        proposal={"strategy": "cover-call"}
    )
    assert opp.symbol == "AAPL"
    assert opp.status == "DETECTED"
    assert isinstance(opp.timestamp, datetime)
    assert opp.context["price"] == 150.0

# 2. Test Service (Mocking Mongo)
@patch("app.services.opportunity_service.MongoClient")
def test_opportunity_service_create(mock_mongo):
    # Setup Mock
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    mock_mongo.return_value = mock_client
    mock_client.get_default_database.return_value = mock_db
    mock_db.opportunities = mock_collection
    mock_collection.insert_one.return_value.inserted_id = "mock_id_123"

    service = OpportunityService()
    
    opp = JuicyOpportunity(
        symbol="GOOG",
        trigger_source="TestService",
        status=OpportunityStatus.DETECTED,
        context={},
        proposal={}
    )
    
    opp_id = service.create_opportunity(opp)
    
    assert opp_id == "mock_id_123"
    mock_collection.create_index.assert_called() # Should verify indexes created
    mock_collection.insert_one.assert_called_once()
    
    # Check inserted data
    inserted_data = mock_collection.insert_one.call_args[0][0]
    assert inserted_data["symbol"] == "GOOG"
    assert inserted_data["status"] == "DETECTED"
    assert "timestamp" in inserted_data

# 3. Test Dividend Scanner Persistence
@patch("app.services.opportunity_service.MongoClient")
@patch("app.services.roll_service.SignalService")
@patch("app.services.roll_service.OpportunityService")
@patch("app.services.dividend_scanner.SignalService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.yf.Ticker")
def test_dividend_scanner_persistence(mock_ticker, mock_opp_service_cls, mock_mongo_client, mock_signal_service, mock_roll_opp_service, mock_roll_signal_service, mock_opp_mongo_client):
    # Mock Ticker Data (Matches criteria: >2% yield, 2-14 days out)
    mock_inst = MagicMock()
    mock_ticker.return_value = mock_inst
    
    # Set ex-div date to 5 days from now
    future_date = datetime.utcnow() + timedelta(days=5)
    
    mock_inst.info = {
         "exDividendDate": future_date.timestamp(),
         "dividendRate": 4.0,
         "currentPrice": 100.0,
         "previousClose": 100.0
    }
    
    # Mock Service Instance
    mock_service = MagicMock()
    mock_opp_service_cls.return_value = mock_service
    
    scanner = DividendScanner()
    results = scanner.scan_dividend_capture_opportunities(["IBM"])
    
    assert len(results) == 1
    assert results[0]["symbol"] == "IBM"
    
    # Verify persistence called
    mock_service.create_opportunity.assert_called_once()
    created_opp = mock_service.create_opportunity.call_args[0][0]
    assert isinstance(created_opp, JuicyOpportunity)
    assert created_opp.symbol == "IBM"
    assert created_opp.trigger_source == "DividendScanner"
    assert created_opp.context["yield_annual"] == 4.0
