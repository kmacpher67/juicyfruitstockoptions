"""
Tests for the profile field returned by GET /ticker/{symbol}.
Covers: profile present in DB, lazy hydration, and yfinance error fallback.
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
    def test_lazy_hydrates_profile_when_absent(self, mock_yf, mock_mongo_cls, client):
        """Profile absent from DB — fetches from yfinance and writes back."""
        stock_doc = {"Ticker": "TST", "Company Name": "Test Corp", "Current Price": 100}
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = stock_doc
        mock_db = MagicMock()
        mock_db.get_default_database.return_value.stock_data = mock_collection
        mock_mongo_cls.return_value = mock_db

        mock_ticker = MagicMock()
        mock_ticker.info = {
            "sector": "Energy",
            "industry": "Oil & Gas",
            "longBusinessSummary": "An energy company.",
            "quoteType": "EQUITY",
            "category": None,
            "exchange": "NYSE",
            "country": "United States",
            "fullTimeEmployees": 5000,
            "website": "https://energy.com",
            "recommendationKey": "hold",
            "numberOfAnalystOpinions": 15,
            "beta": 0.9,
            "forwardPE": 12.0,
            "priceToBook": 1.5,
            "returnOnEquity": 0.10,
            "debtToEquity": 0.8,
            "earningsGrowth": 0.05,
            "revenueGrowth": 0.03,
        }
        mock_ticker.news = [
            {"title": "Energy rally", "publisher": "Bloomberg",
             "link": "http://news.com", "providerPublishTime": 1700000000}
        ]
        mock_yf.Ticker.return_value = mock_ticker

        response = client.get("/api/ticker/TST")

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["sector"] == "Energy"
        assert data["profile"]["recommendation"] == "hold"
        assert len(data["profile"]["news"]) == 1
        # Should have written profile back to DB
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"Ticker": "TST"}
        assert "profile" in call_args[0][1]["$set"]

    @patch('app.api.routes.MongoClient')
    @patch('app.api.routes.yf')
    def test_returns_empty_profile_on_yfinance_error(self, mock_yf, mock_mongo_cls, client):
        """yfinance raises during lazy hydration — profile returned as empty dict, no crash."""
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
        assert data["profile"] == {}
