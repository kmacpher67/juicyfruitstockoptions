from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import get_current_active_user, User
import mongomock
from unittest.mock import MagicMock
import pytest

# Mock DB
@pytest.fixture
def mock_mongo(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/stock_analysis")
    mock_client = mongomock.MongoClient()
    def mock_get_client(*args, **kwargs):
        return mock_client
    
    # Patch pymongo.MongoClient globally to catch all usages
    monkeypatch.setattr("pymongo.MongoClient", mock_get_client)
    
    # Also patch direct usages in modules just in case they imported it before this fixture ran
    # (Though global patch usually works if imported as 'from pymongo import MongoClient')
    monkeypatch.setattr("app.api.routes.MongoClient", mock_get_client)
    monkeypatch.setattr("Ai_Stock_Database.MongoClient", mock_get_client)
    monkeypatch.setattr("app.services.ticker_discovery.MongoClient", mock_get_client)
    
    return mock_client

# Mock User
@pytest.fixture
def client_with_auth():
    app.dependency_overrides[get_current_active_user] = lambda: User(username="testuser", role="admin")
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_get_tracked_defaults_migration(client_with_auth, mock_mongo, monkeypatch):
    """
    Test that if no tracked tickers are in DB, it falls back to defaults 
    AND migrates them to DB (via get_default_tickers logic).
    """
    # Force default list to be known
    defaults = ["TEST1", "TEST2"]
    
    # We strip the real hardcoded list by mocking the fallback return IF the DB read fails?
    # Actually get_default_tickers performs the logic.
    # We should let get_default_tickers run its logic, but we can't easily change the hardcoded list inside it without editing code.
    # So we just verify it returns A list, and that it saves IT to DB.
    
    response = client_with_auth.get("/api/stocks/tracked")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "AAPL" in data
    
    # Verify migration happened
    db = mock_mongo.get_default_database("stock_analysis")
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    assert doc is not None
    assert "AAPL" in doc["tickers"]

def test_add_ticker(client_with_auth, mock_mongo):
    # Pre-seed DB to assume migration happened or list exists
    db = mock_mongo.get_default_database("stock_analysis")
    db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$set": {"tickers": ["AAPL"]}},
        upsert=True
    )

    response = client_with_auth.post("/api/stocks/tracked", json={"ticker": "MSTR"})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    assert "MSTR" in doc["tickers"]
    assert "AAPL" in doc["tickers"]

def test_job_polling(client_with_auth, monkeypatch, mock_mongo):
    # Mock run_stock_live_comparison to verify it was called but not run real logic
    mock_run = MagicMock()
    monkeypatch.setattr("app.api.routes.run_stock_live_comparison", mock_run)

    # Create a job (via add ticker)
    response = client_with_auth.post("/api/stocks/tracked", json={"ticker": "NVDA"})
    assert response.status_code == 200
    job_id = response.json().get("job_id")
    assert job_id

    # Poll it 
    # FastAPI TestClient finishes background tasks before returning control
    status_res = client_with_auth.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()
    assert "status" in job_data
    assert job_data["id"] == job_id
    
    # Verify our mock was called
    mock_run.assert_called_once()

def test_remove_ticker(client_with_auth, mock_mongo):
    # Pre-seed
    db = mock_mongo.get_default_database("stock_analysis")
    db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$set": {"tickers": ["AAPL", "MSTR"]}},
        upsert=True
    )
    
    response = client_with_auth.delete("/api/stocks/tracked/AAPL")
    assert response.status_code == 200
    
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    assert "AAPL" not in doc["tickers"]
    assert "MSTR" in doc["tickers"]

def test_lazy_portfolio_sync(client_with_auth, mock_mongo, monkeypatch):
    # 1. Setup tracked list with AAPL
    db = mock_mongo.get_default_database("stock_analysis")
    db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$set": {"tickers": ["AAPL"]}},
        upsert=True
    )
    
    # 2. Setup IBKR Holdings with new ticker "GOOG"
    # Create valid snapshot
    db.ibkr_holdings.insert_many([
        {"symbol": "GOOG", "date": "2024-01-01", "snapshot_id": "snap1", "asset_class": "STK"},
        {"symbol": "TSLA", "date": "2024-01-01", "snapshot_id": "snap1", "asset_class": "STK"} # TSLA also new
    ])
    
    # Mock run_stock_live_comparison to avoid actual execution error if triggered
    mock_run = MagicMock()
    monkeypatch.setattr("app.api.routes.run_stock_live_comparison", mock_run)

    # 3. Call GET endpoint
    response = client_with_auth.get("/api/stocks/tracked")
    assert response.status_code == 200
    data = response.json()
    
    # 4. Verify "GOOG" and "TSLA" are in response
    assert "AAPL" in data
    assert "GOOG" in data
    assert "TSLA" in data
    
    # 5. Verify DB is updated
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    assert "GOOG" in doc["tickers"]
    assert "TSLA" in doc["tickers"]
