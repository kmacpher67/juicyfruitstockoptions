import pytest
import csv
import io
from unittest.mock import MagicMock, patch
from app.services.export_service import generate_portfolio_csv_content

@patch("app.services.export_service.MongoClient")
def test_export_csv_dirty_data(mock_mongo):
    mock_db = mock_mongo.return_value.get_default_database.return_value
    
    # Mock Holdings with potential problematic data
    mock_db.ibkr_holdings.find_one.return_value = {"report_date": "2026-01-28", "snapshot_id": "123"}
    
    # Scenario 1: Mixed types and Missing values
    mock_db.ibkr_holdings.find.return_value = [
        # Good row
        {"symbol": "TSLA", "market_price": 200.50, "cost_basis": 150.00, "report_date": "2026-01-28"},
        
        # Missing market_price (should default to 0)
        {"symbol": "AAPL", "cost_basis": 100.00, "report_date": "2026-01-28"},
        
        # None market_price
        {"symbol": "MSFT", "market_price": None, "cost_basis": 200.00, "report_date": "2026-01-28"},
        
        # Missing symbol (should use underlying or fallback? logic says fallback to symbol. If both missing?)
        {"market_price": 50, "cost_basis": 40, "report_date": "2026-01-28"},
        
        # None symbols
        {"symbol": None, "underlying_symbol": None, "market_price": 50, "cost_basis": 40},
    ]
    
    try:
        csv_content = generate_portfolio_csv_content()
        print("CSV Generated Successfully")
        print(csv_content)
        
        # Validate output
        lines = csv_content.strip().split('\n')
        assert len(lines) == 6 # Header + 5 rows
        
    except Exception as e:
        pytest.fail(f"Export crashed with: {e}")

@patch("app.services.export_service.MongoClient")
def test_export_csv_empty(mock_mongo):
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_db.ibkr_holdings.find_one.return_value = None
    
    csv_content = generate_portfolio_csv_content()
    assert "Symbol,Current Price" in csv_content
    assert len(csv_content.split('\n')) >= 1
