import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.ibkr_service import parse_and_store_nav, run_ibkr_sync

# Mock MongoDB
@pytest.fixture
def mock_db():
    with patch("app.services.ibkr_service.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        yield mock_db

def test_parse_change_in_nav_date_collision(mock_db):
    """
    Verify that a 1-day ChangeInNAV (Start=End) stores Start as T-1.
    """
    # XML Data: FromDate = ToDate = 20260128
    # StartValue = 100, EndValue = 105
    xml_content = b"""
    <FlexQueryResponse>
        <FlexStatements>
            <FlexStatement>
                <ChangeInNAV accountId="U123" fromDate="20260128" toDate="20260128" 
                             startingValue="100.0" endingValue="105.0" currency="USD" />
            </FlexStatement>
        </FlexStatements>
    </FlexQueryResponse>
    """
    
    parse_and_store_nav(xml_content)
    
    # We expect TWO updates.
    # 1. End Value (Today) -> 2026-01-28 : 105.0
    # 2. Start Value (Yesterday) -> 2026-01-27 : 100.0 (Shifted by 1 day)
    
    calls = mock_db.ibkr_nav_history.update_one.call_args_list
    assert len(calls) == 2
    
    # Analyze calls
    # Call 1: End Value
    # Args: ({filter}, {$set: doc}, upsert=True)
    
    found_end = False
    found_start = False
    
    for call in calls:
        args, kwargs = call
        filter_doc = args[0]
        set_doc = args[1]["$set"]
        
        if filter_doc["_report_date"] == "2026-01-28":
            assert set_doc["ending_value"] == 105.0
            found_end = True
        elif filter_doc["_report_date"] == "2026-01-27":
            # This is the FIX verification
            assert set_doc["ending_value"] == 100.0 # Changed to match logic (Start Value becomes End Value of prev day)
            found_start = True
            
    assert found_end, "Did not find End Value stored for 2026-01-28"
    assert found_start, "Did not find Start Value shifted to 2026-01-27"

@patch("app.services.ibkr_service.fetch_flex_report")
@patch("app.services.ibkr_service.get_system_config")
@patch("app.services.portfolio_analysis.run_portfolio_analysis")
def test_nav_query_selection_ytd(mock_analysis, mock_config, mock_fetch, mock_db):
    """
    Verify nav_days=366 triggers query_id_nav_ytd.
    """
    # Config Setup
    mock_config.return_value = {
        "flex_token": "TEST_TOKEN",
        "query_id_nav_ytd": "YTD_123",
        "query_id_nav_1y": "1Y_456"
    }
    
    # Run Sync
    run_ibkr_sync(nav_days=366)
    
    # Assert fetch called with YTD ID
    mock_fetch.assert_called_with("YTD_123", "TEST_TOKEN", label="nav", date_range=None)

@patch("app.services.ibkr_service.fetch_flex_report")
@patch("app.services.ibkr_service.get_system_config")
@patch("app.services.portfolio_analysis.run_portfolio_analysis")
def test_nav_query_selection_mtd(mock_analysis, mock_config, mock_fetch, mock_db):
    """
    Verify nav_days=31 triggers query_id_nav_mtd.
    """
    # Config Setup
    mock_config.return_value = {
        "flex_token": "TEST_TOKEN",
        "query_id_nav_mtd": "MTD_789"
    }
    
    # Run Sync
    run_ibkr_sync(nav_days=31)
    
    # Assert fetch called with MTD ID
    mock_fetch.assert_called_with("MTD_789", "TEST_TOKEN", label="nav", date_range=None)
