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
    1. Aggregation: Multiple accounts for same Stock -> Merged.
    2. Prioritization: Stock exists -> Option Ignored.
    3. Option Fallback: No stock -> Option used (with x100 multiplier).
    """
    # Mock DB Data
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_collection = mock_db.ibkr_holdings
    
    # Sample Data
    sample_data = [
        # AAPL: Stock in Acct 1
        {
            "symbol": "AAPL",
            "underlying_symbol": "AAPL",
            "avg_cost": 100.0,
            "quantity": 10,
            "report_date": "2026-01-31",
            "asset_class": "STK"
        },
        # AAPL: Stock in Acct 2
        {
            "symbol": "AAPL",
            "underlying_symbol": "AAPL",
            "avg_cost": 110.0,
            "quantity": 20,
            "report_date": "2026-01-31",
            "asset_class": "STK"
        },
        # AAPL: Option (Should be IGNORED because STK exists)
        {
            "symbol": "AAPL  260131P00200000",
            "underlying_symbol": "AAPL",
            "avg_cost": 5.0,
            "quantity": 1,
            "report_date": "2026-01-31",
            "asset_class": "OPT"
        },
        # TSLA: Option Only (Should be used)
        {
            "symbol": "TSLA  260131P00200000",
            "underlying_symbol": "TSLA",
            "avg_cost": 5.0,
            "quantity": 2, # x100 -> 200
            "report_date": "2026-01-31",
            "asset_class": "OPT"
        },
        # CPRX: Short Option (Negative Qty -> Should become Positive)
        {
            "symbol": "CPRX  260131P00200000",
            "underlying_symbol": "CPRX",
            "avg_cost": 1.20,
            "quantity": -1, # x100 -> -100 -> abs -> 100
            "report_date": "2026-01-31",
            "asset_class": "OPT"
        }
    ]
    
    # Mock find_one
    mock_collection.find_one.return_value = {"report_date": "2026-01-31"}
    # Mock find keys
    mock_collection.find.return_value = sample_data
    
    # Execute
    csv_str = generate_portfolio_csv_content()
    
    # Parse Result (Standard CSV)
    lines = csv_str.strip().split("\n")
    header = lines[0].split(",")
    
    rows = []
    for line in lines[1:]:
        values = line.split(",")
        rows.append(dict(zip(header, values)))
    
    assert len(rows) == 3, f"Expected 3 rows (AAPL, CPRX, TSLA), got {len(rows)}"
    
    # Row 1: AAPL
    # Weighted Avg: (10*100 + 20*110) / 30 = (1000 + 2200) / 30 = 3200 / 30 = 106.666...
    row_aapl = next(r for r in rows if r["Symbol"] == "AAPL")
    assert row_aapl["Quantity"] == "30"
    assert row_aapl["Purchase Price"] == "106.67"
    
    # Row 2: TSLA
    # Multipliers: Qty 2 -> 200. Price 5.0 -> 500.0.
    row_tsla = next(r for r in rows if r["Symbol"] == "TSLA")
    assert row_tsla["Quantity"] == "200"
    assert row_tsla["Purchase Price"] == "500.00"

    # Row 3: CPRX (Short Option)
    # Filter: Qty -1 -> -100 -> Abs -> 100.
    row_cprx = next(r for r in rows if r["Symbol"] == "CPRX")
    assert row_cprx["Quantity"] == "100"
