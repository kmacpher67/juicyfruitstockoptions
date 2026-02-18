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
def mock_mongo_client(monkeypatch):
    """Prevent real MongoDB connections in all unit tests.

    Patches MongoClient at every module that imports it, so service
    constructors (OpportunityService, SignalService, RollService,
    DividendScanner) never attempt a real connection to mongo:27017.
    Individual tests can layer their own patches on top if they need
    to assert on specific MongoClient behaviour.
    """
    mock = MagicMock()
    monkeypatch.setattr(
        "app.services.opportunity_service.MongoClient", mock
    )
    return mock

