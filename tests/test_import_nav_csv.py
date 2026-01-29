import pytest
from unittest.mock import MagicMock, patch, mock_open
from app.scripts.import_nav_csv import import_nav_csv
from datetime import datetime

# Sample Data: Stacked CSV (Multiple Accounts)
# Based on inspection of "NAV-2025-Full-Year.csv"
NAV_CSV_CONTENT = """
"ClientAccountID","AccountAlias","CurrencyPrimary","FromDate","ToDate","StartingValue","EndingValue"
"U2842030","","USD","20250101","20251231","600000.00","1017161.90"
"ClientAccountID","AccountAlias","CurrencyPrimary","FromDate","ToDate","StartingValue","EndingValue"
"U280132","","USD","20250101","20251231","290000.00","372029.74"
""".strip()

# Sample for 7-day report
NAV_7DAY_CONTENT = """
"ClientAccountID","AccountAlias","CurrencyPrimary","FromDate","ToDate","StartingValue","EndingValue"
"U2842030","","USD","20260122","20260128","1009000.00","1024341.74"
""".strip()

@pytest.fixture
def mock_mongo():
    with patch('app.scripts.import_nav_csv.MongoClient') as mock:
        yield mock

def test_import_nav_multi_account(mock_mongo):
    """Test parsing a CSV with multiple account blocks."""
    # Setup Mocks
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    
    # Mock File Open
    with patch("builtins.open", mock_open(read_data=NAV_CSV_CONTENT)):
        import_nav_csv("dummy_nav.csv")
        
    # Verify Insert
    assert mock_db.ibkr_nav_history.update_one.call_count == 2
    
    # Check Calls
    calls = mock_db.ibkr_nav_history.update_one.call_args_list
    
    # Call 1: Account U2842030
    args1, _ = calls[0]
    query1, update1 = args1
    doc1 = update1["$set"]
    assert doc1["account_id"] == "U2842030"
    assert doc1["report_date"] == "2025-12-31" # Converted from 20251231
    assert doc1["total_nav"] == 1017161.90
    assert doc1["currency"] == "USD"
    
    # Call 2: Account U280132
    args2, _ = calls[1]
    query2, update2 = args2
    doc2 = update2["$set"]
    assert doc2["account_id"] == "U280132"
    assert doc2["report_date"] == "2025-12-31"
    assert doc2["total_nav"] == 372029.74

def test_import_nav_overwrite(mock_mongo):
    """Test that importing the same date updates existing record (Idempotency)."""
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    
    with patch("builtins.open", mock_open(read_data=NAV_7DAY_CONTENT)):
        import_nav_csv("dummy_7day.csv")
        
    # Query should be by Account AND Date
    args, _ = mock_db.ibkr_nav_history.update_one.call_args
    query = args[0]
    assert query["account_id"] == "U2842030"
    assert query["report_date"] == "2026-01-28"
    assert query["source"] == "NAV_CSV" # Optional metadata
