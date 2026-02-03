from fastapi.testclient import TestClient
from app.main import app
from app.api import routes
from unittest.mock import MagicMock, patch

client = TestClient(app)

# Mock Auth Dependency
async def mock_get_current_active_user():
    return {"username": "testuser", "role": "admin"}

app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user

def test_analyze_rolls_endpoint():
    # Payload
    payload = {
        "symbol": "AAPL",
        "strike": 100.0,
        "expiration": "2025-01-17",
        "position_type": "call"
    }

    mock_response = {
        "current_price": 100.0,
        "rolls": [
            {"strike": 105.0, "expiration": "2025-02-21", "net_credit": 1.5, "score": 85}
        ]
    }

    # Mock RollService
    with patch("app.services.roll_service.RollService") as MockService:
        instance = MockService.return_value
        instance.find_rolls.return_value = mock_response

        response = client.post("/api/analysis/roll", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_price"] == 100.0
        assert len(data["rolls"]) == 1
        assert data["rolls"][0]["score"] == 85
        
        # Verify call args
        instance.find_rolls.assert_called_once_with(
            symbol="AAPL",
            current_strike=100.0,
            current_exp_date="2025-01-17",
            position_type="call"
        )
