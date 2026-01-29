import pytest
from unittest.mock import MagicMock, patch
from app.services.portfolio_analysis import run_portfolio_analysis

@patch("app.services.portfolio_analysis.MongoClient")
def test_drift_detection(mock_mongo):
    """Test that positions > 5% NAV trigger drift alerts."""
    mock_db = mock_mongo.return_value.get_default_database.return_value
    
    # Mock Holdings
    mock_db.ibkr_holdings.find_one.return_value = {"report_date": "2026-01-28", "date": "timestamp"}
    mock_db.ibkr_holdings.find.return_value = [
        {"symbol": "HIGH_CONV", "percent_of_nav": 0.15, "unrealized_pnl": 100}, # 15% - Should alert
        {"symbol": "LOW_CONV", "percent_of_nav": 0.02, "unrealized_pnl": 100},  # 2% - No alert
        {"symbol": "USD", "percent_of_nav": 0.60, "unrealized_pnl": 0}           # Cash - No alert
    ]
    
    run_portfolio_analysis()
    
    # Verify Insights
    assert mock_db.portfolio_insights.insert_many.called
    args = mock_db.portfolio_insights.insert_many.call_args[0][0]
    
    alert = next((a for a in args if a["symbol"] == "HIGH_CONV"), None)
    assert alert is not None
    assert alert["type"] == "DRIFT"
    assert alert["severity"] == "HIGH"
    
    safe = next((a for a in args if a["symbol"] == "LOW_CONV"), None)
    assert safe is None

@patch("app.services.portfolio_analysis.MongoClient")
def test_tax_harvesting(mock_mongo):
    """Test that losses < -$1000 trigger tax alerts."""
    mock_db = mock_mongo.return_value.get_default_database.return_value
    
    mock_db.ibkr_holdings.find_one.return_value = {"report_date": "2026-01-28", "date": "timestamp"}
    mock_db.ibkr_holdings.find.return_value = [
        {"symbol": "LOSER", "percent_of_nav": 0.01, "unrealized_pnl": -1500}, # Should alert
        {"symbol": "WINNER", "percent_of_nav": 0.01, "unrealized_pnl": 500}
    ]
    
    run_portfolio_analysis()
    
    args = mock_db.portfolio_insights.insert_many.call_args[0][0]
    alert = next((a for a in args if a["type"] == "TAX"), None)
    
    assert alert is not None
    assert alert["symbol"] == "LOSER"
    assert alert["severity"] == "MEDIUM"
