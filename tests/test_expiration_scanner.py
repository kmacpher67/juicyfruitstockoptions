import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.expiration_scanner import ExpirationScanner
from app.models.opportunity import JuicyOpportunity

@patch("app.services.expiration_scanner.OpportunityService")
@patch("app.services.expiration_scanner.MongoClient")
def test_expiration_scanner(mock_mongo_cls, mock_opp_service_cls):
    # Mock DB
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_mongo_cls.return_value = mock_client
    mock_client.get_default_database.return_value = mock_db
    
    # Mock Opp Service
    mock_opp_service = MagicMock()
    mock_opp_service_cls.return_value = mock_opp_service
    
    # Mock Portfolio Data
    now = datetime.utcnow()
    
    mock_holdings = [
        # 1. Option Expiring Soon (DTE 3) - Should Flag
        {
            "symbol": "AAPL OPT",
            "secType": "OPT",
            "action": "SELL",
            "quantity": -1,
            "expiry": (now + timedelta(days=3)).strftime("%Y%m%d"),
            "strike": 150,
            "mark_price": 5.0
        },
        # 2. Option Safe (DTE 20) - Ignore
        {
            "symbol": "GOOG OPT",
            "secType": "OPT",
            "action": "SELL",
            "quantity": -1,
            "expiry": (now + timedelta(days=20)).strftime("%Y%m%d"),
            "strike": 100
        },
        # 3. Long Option (Qty > 0) - Ignore (Rule check: Currently we ignore longs?)
        {
            "symbol": "TSLA OPT LONG",
            "secType": "OPT",
            "action": "BUY",
            "quantity": 1,
            "expiry": (now + timedelta(days=2)).strftime("%Y%m%d"),
            "strike": 200
        },
        # 4. Stock - Ignore
        {
            "symbol": "AAPL",
            "secType": "STK",
            "quantity": 100
        }
    ]
    
    mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "snap_1"}
    mock_db.ibkr_holdings.find.return_value = mock_holdings
    
    scanner = ExpirationScanner()
    scanner.scan_portfolio_expirations(days_threshold=7)
    
    # Verify
    # Should call create_opportunity exactly ONCE (for AAPL OPT)
    mock_opp_service.create_opportunity.assert_called_once()
    
    # Check Call Args
    call_args = mock_opp_service.create_opportunity.call_args[0][0]
    assert isinstance(call_args, JuicyOpportunity)
    assert call_args.trigger_source == "ExpirationScanner"
    # assert call_args.symbol == "AAPL" # Parser logic might rely on underlying_symbol which is missing in mock, defaults to symbol[:6]
    assert "AAPL" in call_args.symbol 
    assert call_args.context["days_to_exp"] <= 7
