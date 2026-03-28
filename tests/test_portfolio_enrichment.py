import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.api import routes

from app.models import User

@pytest.fixture
def client():
    """Fixture to provide a TestClient with dependency overrides."""
    async def mock_get_current_active_user():
        return User(username="testuser", role="admin", disabled=False)
    
    app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user
    
    with TestClient(app) as c:
        yield c
    # app.dependency_overrides.clear() is handled by conftest.py autouse fixture

def test_get_portfolio_holdings_enrichment(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        # 1. Mock DB
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db
        
        now = datetime.now()
        snap_id = "test_snap"
        
        mock_holdings = [
            # Stock Uncovered
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 150,
                "report_date": "2026-03-27"
            },
            # Short Call Expiring Soon & ITM
            {
                "symbol": "AAPL  260402C00150000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -1,
                "expiry": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
                "strike": 150.0,
                "mark_price": 160.0, # ITM
                "underlying_symbol": "AAPL"
            }
        ]
        
        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": snap_id}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []
        
        # 2. Mock OptionsAnalyzer
        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        # AAPL has 150 shares and 1 short call (100 shares) -> Partial or Uncovered?
        # Actually, OptionsAnalyzer._group_by_underlying would calculate this.
        # We mock the 'grouped' property that routes.py uses.
        mock_analyzer.grouped = {
            "AAPL": {
                "shares": 150,
                "short_calls": 100,
                "options": [mock_holdings[1]]
            }
        }
        
        # 3. Call API
        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()
        
        # 4. Verify Enrichment
        aapl_stk = next(h for h in data if h["asset_class"] == "STK")
        aapl_opt = next(h for h in data if h["asset_class"] == "OPT")
        
        # Coverage Status
        assert aapl_stk["coverage_status"] == "Uncovered"
        assert aapl_opt["coverage_status"] == "Uncovered" # Both get underlying status
        assert aapl_stk["coverage_mismatch"] is True
        assert aapl_opt["coverage_mismatch"] is True
        
        # DTE & Expiring Flag
        assert aapl_opt["dte"] >= 4 and aapl_opt["dte"] <= 6
        assert aapl_opt["is_expiring_soon"] == True
        
        # ITM & Distance
        assert aapl_opt["is_itm"] == True
        # strike 150, price 160 -> dist (160-150)/150 = 10/150 = 0.0666...
        assert aapl_opt["dist_to_strike_pct"] == pytest.approx(0.0666, 0.1)


def test_get_portfolio_holdings_coverage_is_grouped_by_account(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
            {
                "symbol": "AAPL  260402C00150000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -1,
                "underlying_symbol": "AAPL"
            },
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U2",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {
            "AAPL": {
                "shares": 200,
                "short_calls": 100,
                "options": [mock_holdings[1]]
            }
        }

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        u1_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U1")
        u1_opt = next(h for h in data if h["asset_class"] == "OPT" and h["account_id"] == "U1")
        u2_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U2")

        assert u1_stk["coverage_status"] == "Covered"
        assert u1_stk["coverage_mismatch"] is False
        assert u1_opt["coverage_status"] == "Covered"
        assert u2_stk["coverage_status"] == "Uncovered"
        assert u2_stk["coverage_mismatch"] is True


def test_get_portfolio_holdings_marks_naked_positions_as_mismatch(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "TSLA",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
            {
                "symbol": "TSLA  260402C00200000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -2,
                "underlying_symbol": "TSLA"
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {
            "TSLA": {
                "shares": 100,
                "short_calls": 200,
                "options": [mock_holdings[1]]
            }
        }

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        for row in data:
            assert row["coverage_status"] == "Naked"
            assert row["coverage_mismatch"] is True


def test_get_portfolio_holdings_marks_pure_stock_uncovered_when_using_sectype(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "MSFT",
                "secType": "STK",
                "account_id": "U1",
                "quantity": 200,
                "report_date": "2026-03-27"
            }
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["coverage_status"] == "Uncovered"
        assert data[0]["coverage_mismatch"] is True
        assert data[0]["covered_shares"] == 0
        assert data[0]["share_quantity_total"] == 200


def test_get_portfolio_holdings_coverage_strict_account_coverage(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {"symbol": "AAPL", "asset_class": "STK", "account_id": "U1", "quantity": 100},
            {"symbol": "AAPL  260402C00150000", "asset_class": "OPT", "account_id": "U1", "quantity": -1, "underlying_symbol": "AAPL"},
            {"symbol": "AAPL", "asset_class": "STK", "account_id": "U2", "quantity": 100}
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        u1_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U1")
        u2_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U2")

        assert u1_stk["coverage_status"] == "Covered"
        assert u1_stk["coverage_mismatch"] is False

        assert u2_stk["coverage_status"] == "Uncovered"
        assert u2_stk["coverage_mismatch"] is True
