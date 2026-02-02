

import logging
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.auth.utils import get_password_hash

client = TestClient(app)

@patch("app.api.routes.MongoClient")
def test_login_invalid_user(mock_client):
    """Test login with non-existent user should trigger warning logs."""
    # Setup Mock
    mock_db = MagicMock()
    mock_client.return_value.get_default_database.return_value = mock_db
    mock_db.users.find_one.return_value = None # User not found

    response = client.post(
        "/api/token",
        data={"username": "nonexistentuser", "password": "somerandompassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

@patch("app.api.routes.verify_password")
@patch("app.api.routes.MongoClient")
def test_login_invalid_password(mock_client, mock_verify):
    """Test login with valid user (if exists) but wrong password."""
    # Setup Mock DB
    mock_db = MagicMock()
    mock_client.return_value.get_default_database.return_value = mock_db
    # Return a fake user
    mock_db.users.find_one.return_value = {
        "username": "admin",
        "hashed_password": "hashed_secret"
    }
    
    # Mock verify to fail
    mock_verify.return_value = False

    response = client.post(
        "/api/token",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
