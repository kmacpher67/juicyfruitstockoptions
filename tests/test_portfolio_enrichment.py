import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.api import routes

client = TestClient(app)

# Mock Auth
async def mock_get_current_active_user():
    user = MagicMock()
    user.username = "testuser"
    user.role = "admin"
    return user

app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user

@patch("app.api.routes.MongoClient")
@patch("app.services.options_analysis.OptionsAnalyzer")
def test_get_portfolio_holdings_enrichment(mock_analyzer_cls, mock_mongo_cls):
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
            "quantity": 150,
            "report_date": "2026-03-27"
        },
        # Short Call Expiring Soon & ITM
        {
            "symbol": "AAPL  260402C00150000",
            "asset_class": "OPT",
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
    assert aapl_stk["coverage_status"] == "Partial"
    assert aapl_opt["coverage_status"] == "Partial" # Both get underlying status
    
    # DTE & Expiring Flag
    assert aapl_opt["dte"] >= 4 and aapl_opt["dte"] <= 6
    assert aapl_opt["is_expiring_soon"] == True
    
    # ITM & Distance
    assert aapl_opt["is_itm"] == True
    # strike 150, price 160 -> dist (160-150)/150 = 10/150 = 0.0666...
    assert aapl_opt["dist_to_strike_pct"] == pytest.approx(0.0666, 0.1)
