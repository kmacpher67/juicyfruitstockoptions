import pytest
import io
import csv
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.export_service import generate_portfolio_csv_content

@patch("app.services.export_service.MongoClient")
def test_generate_portfolio_csv_content(mock_mongo):
    """
    Test CSV generation:
    1. Verify columns: Symbol, Current Price, Cost Basis, Date
    2. Verify Options use 'Underlying Symbol'
    3. Verify Formatting
    """
    # Mock DB Data
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_collection = mock_db.ibkr_holdings
    
    # Sample Data: 1 Stock, 1 Option
    sample_data = [
        {
            "symbol": "AAPL",
            "underlying_symbol": "AAPL",
            "market_price": 150.0,
            "cost_basis": 140.0,
            "report_date": "2026-01-31",
            "date": datetime(2026, 1, 31, 12, 0, 0),
            "asset_class": "STK"
        },
        {
            "symbol": "TSLA  260131P00200000", # Option Symbol
            "underlying_symbol": "TSLA",      # Underlying
            "market_price": 5.0,             # Option Price
            "cost_basis": 4.5,
            "report_date": "2026-01-31",
            "date": datetime(2026, 1, 31, 12, 0, 0),
            "asset_class": "OPT"
        }
    ]
    
    # Mock find_one to return a date (simulating 'latest' query)
    mock_collection.find_one.return_value = {"report_date": "2026-01-31", "date": datetime(2026, 1, 31)}
    
    # Mock successful find returning list
    mock_collection.find.return_value = sample_data
    
    # Execute
    csv_str = generate_portfolio_csv_content()
    
    # Parse Result
    f = io.StringIO(csv_str)
    reader = csv.DictReader(f)
    rows = list(reader)
    
    assert len(rows) == 2
    
    # Row 1: AAPL
    assert rows[0]["Symbol"] == "AAPL"
    assert rows[0]["Current Price"] == "150.0"
    assert rows[0]["Cost Basis"] == "140.0"
    assert rows[0]["Date"] == "2026-01-31"
    
    # Row 2: TSLA (Option mapped to Underlying)
    assert rows[1]["Symbol"] == "TSLA"        # KEY REQUIREMENT
    assert rows[1]["Current Price"] == "5.0"  # Option Price
    assert rows[1]["Cost Basis"] == "4.5"     # Option Cost
    assert rows[1]["Date"] == "2026-01-31"
