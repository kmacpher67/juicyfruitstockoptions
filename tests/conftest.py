import os
import sys
from unittest.mock import MagicMock

# MOCK yfinance GLOBALLY to prevent import hang
if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = MagicMock()



# Set MONGO_URI *before* any app modules import settings.
# Outside Docker the default host 'mongo' is unreachable; use localhost.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest


@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Ensure FastAPI dependency overrides are cleared after each test."""
    from app.main import app
    from app.services.data_refresh_queue import get_data_refresh_queue
    yield
    app.dependency_overrides.clear()
    get_data_refresh_queue().clear()

@pytest.fixture(autouse=True)
def mock_mongo_client(monkeypatch):
    """Prevent real MongoDB connections in all unit tests."""
    mock = MagicMock()
    # Patch across major service modules
    modules = [
        "app.services.opportunity_service.MongoClient",
        "app.services.signal_service.MongoClient",
        "app.services.roll_service.MongoClient",
        "app.services.ibkr_service.MongoClient",
        "app.api.routes.MongoClient",
        "app.api.trades.MongoClient",
        "app.database.MongoClient",
        "app.scheduler.jobs.MongoClient"
    ]
    for mod in modules:
        try:
            monkeypatch.setattr(mod, mock)
        except (ImportError, AttributeError):
            pass
    return mock

@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    """Disable the background scheduler during tests."""
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)

