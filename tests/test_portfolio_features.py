from fastapi.testclient import TestClient
from app.main import app
from app.api import routes, trades
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import BackgroundTasks

from app.models import User

@pytest.fixture
def client():
    """Fixture to provide a TestClient with dependency overrides."""
    async def mock_get_current_active_user():
        return User(username="testuser", role="admin", disabled=False)
    
    app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[trades.get_current_active_user] = mock_get_current_active_user
    
    with TestClient(app) as c:
        yield c
    # app.dependency_overrides.clear() is handled by conftest.py autouse fixture

def test_get_ticker_analysis_found(client):
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AAPL",
            "Current Price": 150.0,
            "1D % Change": 1.5,
            "Company Name": "Apple Inc.",
            "profile": {"sector": "Technology"},
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response = client.get("/api/ticker/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["found"] == True
        assert data["data"]["Current Price"] == 150.0
        assert data["is_stale"] is False
        assert data["refresh_queued"] is False
        assert data["data_source"] == "stock_data_db"
        assert data["last_updated"] is not None

def test_get_ticker_analysis_falls_back_to_relaxed_ticker_match(client):
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.side_effect = [
            None,
            {
                "Ticker": "aapl ",
                "Current Price": 150.0,
                "Company Name": "Apple Inc.",
                "profile": {"sector": "Technology"},
            },
        ]

        response = client.get("/api/ticker/aapl")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["found"] is True
        assert data["data"]["Current Price"] == 150.0

        first_call = mock_db.stock_data.find_one.call_args_list[0][0][0]
        second_call = mock_db.stock_data.find_one.call_args_list[1][0][0]
        assert first_call == {"Ticker": "AAPL"}
        assert second_call["Ticker"]["$options"] == "i"

def test_get_ticker_analysis_normalizes_option_like_symbol(client):
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "Current Price": 175.25,
            "Company Name": "Advanced Micro Devices, Inc.",
            "profile": {"sector": "Technology"},
        }

        response = client.get("/api/ticker/AMD 2026-04-02 202.5 Call")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AMD"
        assert data["found"] is True
        assert data["data"]["Ticker"] == "AMD"

def test_get_ticker_analysis_not_found(client):
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        
        response = client.get("/api/ticker/UNKNOWN")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == False
        assert data["price"] == 0.0
        assert data["is_stale"] is True
        assert data["refresh_queued"] is False

def test_get_opportunity_analysis(client):
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "NVDA",
            "IV Rank": 60,
            "Liquidity Rating": 4,
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response = client.get("/api/opportunity/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["juicy_score"] == 30 # 20 (IV) + 10 (Liq)
        assert "High IV Rank" in data["reasons"]
        assert "High Liquidity" in data["reasons"]
        assert data["is_stale"] is False
        assert data["refresh_queued"] is False


def test_get_ticker_analysis_queues_background_refresh_when_stale(client):
    stale_iso = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    with patch("app.api.routes.MongoClient") as mock_client, patch(
        "app.api.routes.run_stock_live_comparison"
    ) as mock_refresh:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AAPL",
            "Current Price": 150.0,
            "Company Name": "Apple Inc.",
            "profile": {"sector": "Technology"},
            "_last_persisted_at": stale_iso,
        }

        response = client.get("/api/ticker/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["is_stale"] is True
        assert data["refresh_queued"] is True
        mock_refresh.assert_called_once_with(["AAPL"], "sync")

def test_get_portfolio_optimizer():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "TSLA",
            "Current Price": 100.0,
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.juicy_opportunities.find.return_value.sort.return_value.limit.return_value = []
        mock_db.juicy_opportunities.find_one.return_value = {
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        payload = routes.get_portfolio_optimizer("TSLA", bt, include_meta=False, current_user=admin)

        assert len(payload) >= 1
        assert payload[0]["strategy"] == "Covered Call"
        # 100 * 1.05 = 105
        assert payload[0]["strike_target"] == 105.0
        assert payload[0]["type"] == "CALL"
        assert "create_date" in payload[0]
        assert "last_updated" in payload[0]


def test_get_juicys_workspace_rows():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.juicy_opportunities.find.return_value.sort.return_value.limit.return_value = [
            {
                "symbol": "TSLA",
                "as_of": datetime.now(timezone.utc).isoformat(),
                "strategy": "Covered Call",
                "type": "CALL",
                "action": "SELL",
                "dte": 30,
                "strike": 105.0,
                "premium": 5.0,
                "yield_pct": 12.5,
                "score": 88,
                "reason_summary": "Covered Call | yield 12.5%",
                "create_date": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        ]

        payload = routes.get_juicys(admin, preset="juicy", limit=20)
        assert payload["count"] == 1
        assert payload["rows"][0]["symbol"] == "TSLA"


def test_refresh_juicys_enqueues_job():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient"), patch("app.api.routes.background_job_wrapper", return_value=None):
        payload = routes.refresh_juicys(bt, admin, symbol="TSLA")
    assert payload["status"] == "queued"
    assert payload["job_id"]

def test_trade_analysis_date_filter(client):
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 100.0, "code_date": "20240115", "DateTime": "20240115"},
    ]
    
    with patch("app.api.trades.MongoClient") as mock_client, \
         patch("app.services.trade_analysis.yf") as mock_yf:
         
        mock_ticker = MagicMock()
        mock_ticker.fast_info.get.return_value = 150.0
        mock_yf.Tickers.return_value.tickers.get.return_value = mock_ticker
        
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
