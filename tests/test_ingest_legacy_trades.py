import pytest
import io
from unittest.mock import MagicMock, mock_open, patch
from ingest_legacy_trades import normalize_row, ingest_file
from contextlib import contextmanager

# Test Data
SAMPLE_ROW_2024 = {
    "ClientAccountID": "U12345",
    "Symbol": "AAPL",
    "TradeID": "11223344",
    "Quantity": "100",
    "TradePrice": "150.50",
    "Model": "MyModel", # Extra Field
    "IBCommission": "-1.0"
}

SAMPLE_ROW_LEGACY = {
    "Symbol": "MSFT",
    "TransactionID": "998877", # Legacy ID Key
    "Quantity": "50",
    "TradePrice": "200"
}

def test_normalize_row_standard():
    """Test normalization of a standard 2024 row."""
    result = normalize_row(SAMPLE_ROW_2024)
    assert result["TradeID"] == "11223344"
    assert result["Quantity"] == 100.0
    assert result["TradePrice"] == 150.5
    assert result["Model"] == "MyModel"
    assert "ClientAccountID" in result

def test_normalize_row_legacy():
    """Test normalization of a legacy row with TransactionID."""
    result = normalize_row(SAMPLE_ROW_LEGACY)
    assert result["TradeID"] == "998877" # Normalized
    assert result["Symbol"] == "MSFT"
    assert result["Quantity"] == 50.0

def test_normalize_row_missing_id():
    """Row without ID should be skipped."""
    row = {"Symbol": "SUBTOTAL", "Quantity": "100"}
    assert normalize_row(row) is None

def test_ingest_file():
    """Test full file ingestion flow with mocks."""
    # Mock File Content
    # Lines: Header, Data Record 1, Data Record 2
    mock_csv_content = (
        '"ClientAccountID","Symbol","TradeID","Quantity","TradePrice"\n'
        '"U1","AAPL","T1","10","100"\n'
        '"U1","GOOG","T2","5","2000"\n'
    )
    
    
    mock_db = MagicMock()
    mock_collection = mock_db.ibkr_trades
    
    # Mock open using StringIO to support seek/readlines/iter correctly
    class MockFile(io.StringIO):
        def __enter__(self): return self
        def __exit__(self, *args): pass

    with patch("builtins.open", side_effect=lambda *args, **kwargs: MockFile(mock_csv_content)):
        with patch("os.path.basename", return_value="test.csv"):
            ingest_file("dummy/path/test.csv", mock_db)
            
    # Verification
    # Should resolve to 2 calls to update_one
    assert mock_collection.update_one.call_count == 2
    
    # Check arguments of first call
    # update_one({"trade_id": "T1"}, {"$set": {...}}, upsert=True)
    args, kwargs = mock_collection.update_one.call_args_list[0]
    query = args[0]
    update = args[1]
    
    assert query == {"trade_id": "T1"}
    assert update["$set"]["trade_id"] == "T1"
    assert update["$set"]["symbol"] == "AAPL" # From alias mapping? No, ingest script passes dict matching Model aliases
    # Wait, TradeRecord uses alias="Symbol". 
    # normalize_row returns "Symbol": "AAPL". 
    # TradeRecord(Symbol="AAPL") -> field is 'symbol'.
    # model_dump() -> {'symbol': 'AAPL', ...}
    # So the stored document should have 'symbol'.
    
    assert update["$set"]["symbol"] == "AAPL"
    assert kwargs["upsert"] is True

def test_ingest_file_skip_orphans():
    """Test that rows without TradeID are skipped (subtotals etc)."""
    mock_csv_content = (
        '"Symbol","Quantity","Notes"\n'
        '"Total","100","Subtotal Line"\n' # No TradeID column or value
    )
    
    mock_db = MagicMock()
    mock_collection = mock_db.ibkr_trades

    class MockFile(io.StringIO):
        def __enter__(self): return self
        def __exit__(self, *args): pass

    with patch("builtins.open", side_effect=lambda *args, **kwargs: MockFile(mock_csv_content)):
         with patch("os.path.basename", return_value="subtotals.csv"):
            ingest_file("subtotals.csv", mock_db)
            
    assert mock_collection.update_one.call_count == 0
