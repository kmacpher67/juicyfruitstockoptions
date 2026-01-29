import pytest
from unittest.mock import MagicMock, patch, mock_open
from app.scripts.import_manual_csv import import_portfolio_csv, import_trades_csv
from datetime import datetime

# Sample Data
PORTFOLIO_CSV_CONTENT = """
"BOF","U110638","Daily_Portfolio","1","20260128","20260128"
"Header","Trash"
"Symbol","Description","UnderlyingSymbol","Quantity","MarkPrice","PositionValue","CostBasisPrice"
"AAPL","Apple Inc","AAPL","10","150.0","1500.0","140.0"
"GOOG","Google","GOOG","5","2000.0","10000.0","1900.0"
""".strip()

TRADES_CSV_CONTENT = """
"Trash","Header"
"Symbol","Buy/Sell","TradeID","Quantity","TradePrice","IBCommission"
"AAPL","BUY","12345","10","150.0","1.0"
"""

@pytest.fixture
def mock_mongo():
    with patch('app.scripts.import_manual_csv.MongoClient') as mock:
        yield mock

def test_import_portfolio_csv(mock_mongo):
    # Setup Mocks
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    
    # Configure count_documents return value (simulate existing doc finding 1 match)
    mock_db.ibkr_holdings.count_documents.return_value = 1
    
    # Mock File Open
    with patch("builtins.open", mock_open(read_data=PORTFOLIO_CSV_CONTENT)):
        import_portfolio_csv("dummy_path.csv")
        
    # Verify Insert
    assert mock_db.ibkr_holdings.insert_many.called
    args = mock_db.ibkr_holdings.insert_many.call_args[0][0]
    assert len(args) == 2
    assert args[0]["symbol"] == "AAPL"
    assert args[0]["quantity"] == 10.0
    assert args[0]["snapshot_id"] == datetime(2026, 1, 28)
    
    # Verify Idempotency Check (Delete called because count_documents returned 1)
    mock_db.ibkr_holdings.delete_many.assert_called_with({"snapshot_id": datetime(2026, 1, 28)})

def test_import_trades_csv(mock_mongo):
    # Setup Mocks
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    
    # Mock File Open
    with patch("builtins.open", mock_open(read_data=TRADES_CSV_CONTENT)):
        import_trades_csv("dummy_path.csv")
        
    # Verify Upsert
    assert mock_db.ibkr_trades.update_one.called
    assert mock_db.ibkr_trades.update_one.call_count == 1
    
    call_args = mock_db.ibkr_trades.update_one.call_args
    query = call_args[0][0]
    update = call_args[0][1]
    
    assert query["trade_id"] == "12345"
    assert update["$set"]["symbol"] == "AAPL"
    assert update["$set"]["quantity"] == 10.0
