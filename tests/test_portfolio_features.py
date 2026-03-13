from fastapi.testclient import TestClient
from app.main import app
from app.api import routes, trades
from unittest.mock import MagicMock, patch
import pytest

client = TestClient(app)

# Mock Auth
async def mock_get_current_active_user():
    return {"username": "testuser", "role": "admin"}

app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user
app.dependency_overrides[trades.get_current_active_user] = mock_get_current_active_user

def test_get_ticker_analysis_found():
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AAPL",
            "Current Price": 150.0,
            "1D % Change": 1.5
        }
        
        response = client.get("/api/ticker/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["found"] == True
        assert data["data"]["Current Price"] == 150.0

def test_get_ticker_analysis_not_found():
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        
        response = client.get("/api/ticker/UNKNOWN")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == False
        assert data["price"] == 0.0

def test_get_opportunity_analysis():
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "NVDA",
            "IV Rank": 60,
            "Liquidity Rating": 4
        }
        
        response = client.get("/api/opportunity/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["juicy_score"] == 30 # 20 (IV) + 10 (Liq)
        assert "High IV Rank" in data["reasons"]
        assert "High Liquidity" in data["reasons"]

def test_get_portfolio_optimizer():
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "TSLA",
            "Current Price": 100.0
        }
        
        response = client.get("/api/portfolio/optimizer/TSLA")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["strategy"] == "Covered Call"
        # 100 * 1.05 = 105
        assert data[0]["strike_target"] == 105.0

def test_trade_analysis_date_filter():
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 100.0, "code_date": "20240115", "DateTime": "20240115"},
    ]
    
    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_cursor
        mock_db.ibkr_trades.find.return_value = mock_find
        
        # Test valid range
        response = client.get("/api/trades/analysis?start_date=2024-01-01&end_date=2024-01-31")
        assert response.status_code == 200
        
        # Verify call args
        args, _ = mock_db.ibkr_trades.find.call_args
        query = args[0]
        # We NO LONGER expect date_time filter in DB query, it is applied post-PNL calculation
        assert "date_time" not in query
        
        data = response.json()
        assert "trades" in data
        assert "metrics" in data
