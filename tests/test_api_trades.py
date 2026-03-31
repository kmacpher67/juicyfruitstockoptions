from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Patch out background tasks that cause DB hangs before importing app
patch("app.scheduler.jobs.start_scheduler").start()
patch("app.scheduler.jobs.stop_scheduler").start()

from app.main import app
from app.api import trades

import pytest
from app.models import User

@pytest.fixture
def client():
    """Fixture to provide a TestClient with dependency overrides."""
    async def mock_get_current_active_user():
        return User(username="testuser", role="admin", disabled=False)
    
    app.dependency_overrides[trades.get_current_active_user] = mock_get_current_active_user
    
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_get_trades_endpoint(client):
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
        
        # Check for either symbol or Symbol depending on serialization model
        symbol = data[0].get("symbol") or data[0].get("Symbol")
        # Assert GOOG because 20240102 > 20240101 and the API now sorts descending by date_time
        assert symbol == "GOOG"

def test_get_analysis_endpoint(client):
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


def test_get_trade_live_status_endpoint(client):
    fake_tws_service = MagicMock()
    fake_tws_service.get_live_status.return_value = {
        "connected": True,
        "connection_state": "connected",
        "diagnosis": "IBKR TWS API session connected.",
        "last_execution_update": "2026-03-31T12:15:00",
        "tws_enabled": True,
    }

    with patch("app.api.trades.MongoClient") as mock_client, \
         patch("app.api.trades.get_ibkr_tws_service", return_value=fake_tws_service):
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.count_documents.return_value = 3
        mock_db.ibkr_trades.find_one.return_value = {
            "trade_id": "abc123",
            "source": "tws_live",
            "date_time": "20260331 12:14:59",
            "last_tws_update": "2026-03-31T12:15:00",
        }

        response = client.get("/api/trades/live-status")
        assert response.status_code == 200

        data = response.json()
        assert data["connection_state"] == "connected"
        assert data["today_live_trade_count"] == 3
        assert data["latest_live_trade_at"] == "2026-03-31T12:15:00"
