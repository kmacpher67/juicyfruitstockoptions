import sys
from unittest.mock import MagicMock

# 1. Mock problematic modules BEFORE importing anything else
mock_yf = MagicMock()
sys.modules["yfinance"] = mock_yf

# 2. Now import app modules
import pytest
from unittest.mock import patch
from app.services.scanner_service import scan_momentum_calls
from app.services.roll_service import RollService
from app.services.signal_service import SignalService

@pytest.fixture
def mock_mongo():
    with patch("app.services.scanner_service.MongoClient") as mock_client: 
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        mock_client.return_value.__getitem__.return_value = mock_db 
        yield mock_db

@pytest.fixture
def mock_opp_service():
    with patch("app.services.roll_service.OpportunityService") as mock_roll_opp, \
         patch("app.services.scanner_service.OpportunityService") as mock_scan_opp, \
         patch("app.services.signal_service.OpportunityService") as mock_signal_opp:
         
        mock_service = MagicMock()
        mock_roll_opp.return_value = mock_service
        mock_scan_opp.return_value = mock_service
        mock_signal_opp.return_value = mock_service
        yield mock_service

def test_scan_momentum_calls_persistence(mock_mongo, mock_opp_service):
    # Setup Mock Data
    mock_mongo.stock_data.find.return_value.limit.return_value = [
        {"Ticker": "AAPL", "Current Price": 150, "TSMOM_60": 0.1, "EMA_20_highlight": 0.01}
    ]
    
    # Run
    results = scan_momentum_calls(persist=True)
    
    # Verify
    assert len(results) == 1
    mock_opp_service.create_opportunity.assert_called_once()
    args, _ = mock_opp_service.create_opportunity.call_args
    opp = args[0]
    assert opp.symbol == "AAPL"
    assert opp.trigger_source == "MomentumScanner"

def test_roll_service_persistence(mock_opp_service):
    # Mock Data
    items = [
        {
            "symbol": "TSLA",
            "secType": "OPT",
            "right": "C",
            "expiry": "2025-01-01",
            "quantity": -1,
            "strike": 200,
            "averageCost": 5.0
        }
    ]
    
    service = RollService()
    
    # We need to mock find_rolls to return high score rolls
    with patch.object(service, 'find_rolls') as mock_find:
        mock_find.return_value = {
            "symbol": "TSLA",
            "current_price": 200,
            "rolls": [
                {"strike": 205, "score": 80, "roll_type": "Up & Out", "net_credit": 1.0}, # Keep
                {"strike": 210, "score": 50, "roll_type": "Up & Out", "net_credit": 0.5}  # Ignore (Score < 60)
            ]
        }
        
        # Run
        suggestions = service.analyze_portfolio_rolls(items, persist=True)
        
        # Verify
        assert len(suggestions) == 1
        mock_opp_service.create_opportunity.assert_called_once()
        args, _ = mock_opp_service.create_opportunity.call_args
        opp = args[0]
        assert opp.symbol == "TSLA"
        assert opp.trigger_source == "SmartRoll"
        assert opp.context["score"] == 80

def test_signal_service_persistence(mock_opp_service):
    service = SignalService()
    
    # Configure global mock_yf for download
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.__len__.return_value = 100
    mock_df.columns = ["Close"] # Simple
    
    mock_yf.download.return_value = mock_df
    
    # Mock internal methods
    with patch.object(service, 'get_kalman_signal', return_value={"signal": "Bullish", "kalman_mean": 100, "current_price": 105}), \
         patch.object(service, 'get_markov_probabilities', return_value={
             "transitions": {"UP_BIG": 0.4, "UP_SMALL": 0.3, "DOWN_BIG": 0.1} 
         }):
         
         service.scan_and_persist_signals(["NVDA"])
         
         mock_yf.download.assert_called()
         
         mock_opp_service.create_opportunity.assert_called_once()
         args, _ = mock_opp_service.create_opportunity.call_args
         opp = args[0]
         assert opp.symbol == "NVDA"
         assert opp.trigger_source == "SignalService"
         assert "prob_up" in opp.context
         assert opp.context["prob_up"] == 0.7
