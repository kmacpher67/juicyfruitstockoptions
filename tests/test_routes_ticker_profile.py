"""
Tests for the profile field returned by GET /ticker/{symbol}.
Covers: profile present in DB and DB-first fallback behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.models import User
import app.auth.dependencies

MOCK_PROFILE = {
    "sector": "Technology",
    "industry": "Semiconductors",
    "description": "A great company.",
    "style": "EQUITY",
    "category": "",
    "exchange": "NMS",
    "country": "United States",
    "employees": 10000,
    "website": "https://example.com",
    "recommendation": "buy",
    "analyst_opinions": 30,
    "beta": 1.5,
    "forward_pe": 25.0,
    "price_to_book": 5.0,
    "roe": 0.35,
    "debt_to_equity": 0.5,
    "earnings_growth": 0.20,
    "revenue_growth": 0.15,
    "news": [{"title": "Big news", "publisher": "Reuters", "link": "http://x.com", "published_at": "2024-01-01 12:00"}],
}


@pytest.fixture
def client():
    async def mock_user():
        return User(username="testuser", email="test@example.com", role="admin", hashed_password="pw", disabled=False)

    fastapi_app.dependency_overrides[app.auth.dependencies.get_current_active_user] = mock_user
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


class TestTickerProfileEndpoint:

    @patch('app.api.routes.MongoClient')
    def test_returns_profile_from_db(self, mock_mongo_cls, client):
        """Profile already in DB — returned directly, no yfinance call."""
        stock_doc = {
            "Ticker": "TST",
            "Company Name": "Test Corp",
            "Current Price": 100,
            "profile": MOCK_PROFILE,
        }
        mock_db = MagicMock()
        mock_db.get_default_database.return_value.stock_data.find_one.return_value = stock_doc
        mock_mongo_cls.return_value = mock_db

        with patch('app.api.routes.yf') as mock_yf:
            response = client.get("/api/ticker/TST")

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert "profile" in data
        assert data["profile"]["sector"] == "Technology"
        assert data["profile"]["recommendation"] == "buy"
        assert len(data["profile"]["news"]) == 1
        # yfinance should NOT have been called for profile since it was in DB
        mock_yf.Ticker.assert_not_called()

    @patch('app.api.routes.MongoClient')
    @patch('app.api.routes.yf')
    def test_returns_empty_profile_when_absent_without_yfinance(self, mock_yf, mock_mongo_cls, client):
        """Profile absent from DB — endpoint remains DB-first and does not call yfinance."""
        stock_doc = {"Ticker": "TST", "Company Name": "Test Corp", "Current Price": 100}
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = stock_doc
        mock_db = MagicMock()
        mock_db.get_default_database.return_value.stock_data = mock_collection
        mock_mongo_cls.return_value = mock_db

        response = client.get("/api/ticker/TST")

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["profile"] == {"news": []}
        mock_collection.update_one.assert_not_called()
        mock_yf.Ticker.assert_not_called()

    @patch('app.api.routes.MongoClient')
    @patch('app.api.routes.yf')
    def test_returns_empty_profile_without_calling_yfinance_when_missing(self, mock_yf, mock_mongo_cls, client):
        """Even if yfinance is broken, DB-first response succeeds when profile is missing."""
        stock_doc = {"Ticker": "TST", "Company Name": "Test Corp", "Current Price": 100}
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = stock_doc
        mock_db = MagicMock()
        mock_db.get_default_database.return_value.stock_data = mock_collection
        mock_mongo_cls.return_value = mock_db

        mock_yf.Ticker.side_effect = Exception("yfinance unavailable")

        response = client.get("/api/ticker/TST")

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["profile"] == {"news": []}
        mock_yf.Ticker.assert_not_called()
