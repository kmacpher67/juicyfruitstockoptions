
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.models import User
import app.auth.dependencies

# ... rest remains same ...
import pytest
from unittest.mock import patch, MagicMock

client = TestClient(fastapi_app)

def mock_get_current_active_user():
    return User(username="testuser", email="test@example.com", role="admin", hashed_password="pw", disabled=False)

fastapi_app.dependency_overrides[app.auth.dependencies.get_current_active_user] = mock_get_current_active_user

class TestSignalAPI:

    @patch('app.api.routes.SignalService')
    @patch('app.api.routes.yf.download')
    def test_get_ticker_signals(self, mock_yf, mock_service_cls):
        # Mock YF Data
        import pandas as pd
        df = pd.DataFrame({'Close': [100, 101]})
        # Handle the multi-index check logic in the route
        # Route checks: if isinstance(data.columns, pd.MultiIndex): ...
        # Simple dataframe doesn't have multi-index columns by default
        mock_yf.return_value = df
        
        # Mock Service Response
        service_instance = mock_service_cls.return_value
        service_instance.get_kalman_signal.return_value = {"signal": "Bullish", "current": 101}
        service_instance.get_markov_probabilities.return_value = {"current_state": "UP", "transitions": {}}
        
        response = client.get("/api/analysis/signals/SPY")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "SPY"
        assert data["kalman"]["signal"] == "Bullish"

    @patch('app.api.routes.yf.download')
    def test_get_ticker_signals_error_handling(self, mock_yf):
        mock_yf.side_effect = Exception("API Error")
        response = client.get("/api/analysis/signals/SPY")
        assert response.status_code == 500
