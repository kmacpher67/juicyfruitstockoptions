from fastapi.testclient import TestClient
from app.main import app
from app.api import trades
from unittest.mock import MagicMock, patch

client = TestClient(app)

# Mock Auth Dependency to bypass login
async def mock_get_current_active_user():
    return {"username": "testuser", "role": "admin"}

app.dependency_overrides[trades.get_current_active_user] = mock_get_current_active_user

def test_get_trades_endpoint():
    # Mock DB response
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 150.0, "DateTime": "20240101"},
        {"TradeID": "2", "Symbol": "GOOG", "Quantity": 5, "TradePrice": 2000.0, "DateTime": "20240102"}
    ]
    
    # We need to mock pymongo within trades.py
    # Since get_db creates a new client, we mock MongoClient
    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        # Mock cursor for find()
        mock_find = MagicMock()
        mock_find.sort.return_value.skip.return_value.limit.return_value = mock_cursor
        mock_db.ibkr_trades.find.return_value = mock_find
        
        # Mock dividends
        mock_db.ibkr_dividends.find.return_value.limit.return_value = []
        
        response = client.get("/api/trades/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        print(f"DEBUG RESPONSE KEYS: {data[0].keys()}")
        # Check for either symbol or Symbol depending on serialization model
        symbol = data[0].get("symbol") or data[0].get("Symbol")
        # Assert GOOG because 20240102 > 20240101 and the API now sorts descending by date_time
        assert symbol == "GOOG"

def test_get_analysis_endpoint():
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 100.0, "DateTime": "20240101"},
        {"TradeID": "2", "Symbol": "AAPL", "Quantity": -10, "TradePrice": 110.0, "DateTime": "20240102"} 
    ]
    
    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.find.return_value.sort.return_value = mock_cursor
        
        # Mock dividends
        mock_db.ibkr_dividends.find.return_value = []
        
        response = client.get("/api/trades/analysis?symbol=AAPL")
        assert response.status_code == 200
        data = response.json()
        
        assert "trades" in data
        assert "metrics" in data
        assert data["metrics"]["total_pl"] == 100.0
        assert data["metrics"]["win_rate"] == 100.0
