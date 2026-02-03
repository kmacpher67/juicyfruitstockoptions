
import os
import shutil
import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
from fastapi.testclient import TestClient
from app.api.routes import router

# Setup Test Client
# We might need to mock the dependencies for the router if it has any top-level execution
# For this specific function, it imports inside the function, which is good for testing isolation.

client = TestClient(router)

@pytest.fixture
def mock_xdivs_dir():
    # Setup
    test_dir = "xdivs"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Clean before test
    for f in os.listdir(test_dir):
        if f.startswith("dividends_test"):
            os.remove(os.path.join(test_dir, f))
            
    yield test_dir
    
    # Teardown - leave directory but clean test files?
    # Actual implementation uses real date, so we need to be careful not to delete real files if running on production machine
    pass

@patch("app.api.routes.MongoClient")
@patch("app.api.routes.yf.Ticker")
def test_get_dividend_calendar_generation(mock_ticker, mock_mongo, mock_xdivs_dir):
    """Test that the endpoint generates a file when none exists."""
    
    # RE-STRATEGY: Mock usage of DividendScanner inside the route
    # Since import is local to function, we must patch the source class
    with patch("app.services.dividend_scanner.DividendScanner") as MockScanner:
        mock_instance = MockScanner.return_value
        expected_file_path = "xdivs/dividends_2099-01-01.ics"
        
        # Define side effect to create file ONLY when called (simulating generation)
        def create_dummy_file():
             if not os.path.exists("xdivs"): os.makedirs("xdivs")
             with open(expected_file_path, "w") as f:
                 f.write("DUMMY ICS CONTENT")
             return expected_file_path

        mock_instance.generate_dividend_calendar.side_effect = create_dummy_file
        
        # Ensure file does NOT exist before call
        if os.path.exists(expected_file_path):
             os.remove(expected_file_path)

        # Mock Date for the cache check filename matching
        with patch("app.api.routes.datetime") as mock_dt_module:
             # Route calls datetime.utcnow().strftime...
             # We want formatting to result in '2099-01-01'
             mock_dt_module.utcnow.return_value = datetime(2099, 1, 1)

             from app.api.routes import get_dividend_calendar
             
             # CALL
             response = get_dividend_calendar()
             
             # VERIFY
             assert response.path == expected_file_path
             MockScanner.assert_called()
             mock_instance.generate_dividend_calendar.assert_called_once()
             
        # Cleanup
        if os.path.exists(expected_file_path):
             os.remove(expected_file_path)

@patch("app.api.routes.MongoClient")
def test_get_dividend_calendar_cache_hit(mock_mongo):
    """Test that we serve existing file without hitting DB."""
    
    # 1. Setup Mock Today
    fixed_date = "2099-01-02"
    expected_file = f"xdivs/dividends_{fixed_date}.ics"
    
    # Create Dummy File
    if not os.path.exists("xdivs"):
        os.makedirs("xdivs")
    with open(expected_file, "w") as f:
        f.write("DUMMY CONTENT")
        
    with patch("app.api.routes.datetime") as mock_dt_module:
        mock_dt_module.utcnow.return_value = datetime(2099, 1, 2)
        
        from app.api.routes import get_dividend_calendar
        
        # CALL
        response = get_dividend_calendar()
        
        # VERIFY
        # Mongo should NOT be called
        mock_mongo.assert_not_called()
        
        # Response should be file response? 
        # Fastapi FileResponse is returned.
        # We can check if response object is FileResponse
        assert response.path == expected_file

    # Clean up
    if os.path.exists(expected_file):
        os.remove(expected_file)
