import pytest
from unittest.mock import MagicMock, patch
from app.services.scanner_service import run_scanner, scan_momentum_calls

@pytest.fixture
def mock_collection():
    with patch("app.services.scanner_service.get_stock_collection") as mock_get:
        mock_col = MagicMock()
        mock_get.return_value = mock_col
        yield mock_col

def test_run_scanner_basic(mock_collection):
    # Setup
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = [{"Ticker": "AAPL"}]
    mock_collection.find.return_value = mock_cursor
    
    # Act
    criteria = {"Ticker": "AAPL"}
    results = run_scanner(criteria)
    
    # Assert
    assert results == [{"Ticker": "AAPL"}]
    mock_collection.find.assert_called_with(criteria, {"_id": 0})

def test_scan_momentum_calls(mock_collection):
    # Setup
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = [{"Ticker": "NVDA"}]
    mock_collection.find.return_value = mock_cursor
    
    # Act
    results = scan_momentum_calls()
    
    # Assert
    assert len(results) == 1
    call_args = mock_collection.find.call_args
    query = call_args[0][0]
    
    # Verify Filters
    assert query["TSMOM_60"]["$gt"] == 0.05
    assert query["Current Price"]["$gt"] == 10
    assert query["EMA_20_highlight"]["$gt"] == 0.005
