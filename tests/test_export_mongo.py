import pytest
import os
import json
import mongomock
from unittest.mock import patch, MagicMock
from export_mongo import export_data
from Ai_Stock_Database import AiStockDatabase

@pytest.fixture
def mock_mongo():
    """Mock the AiStockDatabase connection."""
    with patch('export_mongo.AiStockDatabase') as MockDB:
        # Create a mock instance
        mock_instance = MagicMock()
        MockDB.return_value = mock_instance
        
        # Use mongomock for the actual collection behavior
        mongo_client = mongomock.MongoClient()
        db = mongo_client.db
        collection = db.collection
        
        # Wire up the mock instance to use the mongomock collection
        mock_instance.collection = collection
        mock_instance.collection_name = "test_collection"
        
        yield collection

def test_export_data_creates_file(mock_mongo, tmp_path):
    """Test that export_data creates a file with correct data."""
    # Setup: Insert some sample data
    sample_data = [
        {"Ticker": "AAPL", "Price": 150.0},
        {"Ticker": "GOOG", "Price": 2800.0}
    ]
    mock_mongo.insert_many(sample_data)
    
    # Define output file in temp dir
    output_file = tmp_path / "test_backup.json"
    
    # Execute
    export_data(output_file=str(output_file))
    
    # Verify
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        data = json.load(f)
        
    assert len(data) == 2
    # Verify content (order might vary, so check presence)
    tickers = [d['Ticker'] for d in data]
    assert "AAPL" in tickers
    assert "GOOG" in tickers

def test_export_data_empty_collection(mock_mongo, tmp_path):
    """Test that export_data handles empty collections gracefully."""
    # Setup: No data inserted
    
    output_file = tmp_path / "empty_backup.json"
    
    # Execute
    export_data(output_file=str(output_file))
    
    # Verify: Should NOT create a file if empty (based on current implementation logic check)
    # The current implementation has:
    # if count == 0: return
    
    assert not output_file.exists()

def test_export_data_bson_serialization(mock_mongo, tmp_path):
    """Test that BSON types (ObjectId, datetime) are handled correctly."""
    from datetime import datetime
    import bson
    
    sample_data = {
        "Ticker": "MSFT",
        "Last Update": datetime(2023, 1, 1, 12, 0, 0),
        "_id": bson.ObjectId()
    }
    mock_mongo.insert_one(sample_data)
    
    output_file = tmp_path / "bson_backup.json"
    
    export_data(output_file=str(output_file))
    
    with open(output_file, 'r') as f:
        content = f.read()
        
    # Check that it's valid JSON
    data = json.loads(content)
    assert len(data) == 1
    assert data[0]['Ticker'] == "MSFT"
    # Check that ObjectId was serialized (usually becomes specific dict structure or string depending on json_util)
    assert '$oid' in str(content) or '_id' in data[0]

