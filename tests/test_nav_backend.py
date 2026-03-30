import asyncio
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.models import NavReportType, IBKRConfig
from app.services.ibkr_service import fetch_and_store_nav_report, get_nav_query_id
from app.api.routes import (
    get_nav_report_endpoint,
    get_portfolio_live_nav,
    get_portfolio_live_status,
    get_portfolio_stats,
)

# --- Fixtures ---

@pytest.fixture
def mock_config():
    return {
        "flex_token": "fake_token",
        "query_id_nav_1d": "1001",
        "query_id_nav_7d": "1007"
    }

# --- Service Tests ---

def test_get_nav_query_id(mock_config):
    assert get_nav_query_id(NavReportType.NAV_1D, mock_config) == "1001"
    assert get_nav_query_id(NavReportType.NAV_7D, mock_config) == "1007"
    assert get_nav_query_id(NavReportType.NAV_30D, mock_config) is None

@patch("app.services.ibkr_service.get_system_config")
@patch("app.services.ibkr_service.fetch_flex_report")
@patch("app.services.ibkr_service.parse_and_store_nav")
@patch("app.services.ibkr_service.MongoClient")
@patch("app.services.ibkr_service.save_sync_status")
def test_fetch_and_store_nav_report(mock_save_status, mock_mongo, mock_parse, mock_fetch, mock_get_config, mock_config):
    mock_get_config.return_value = mock_config
    mock_fetch.return_value = b"<xml>data</xml>"
    
    # Test Success
    result = fetch_and_store_nav_report(NavReportType.NAV_1D)
    
    assert result["status"] == "success"
    mock_fetch.assert_called_with("1001", "fake_token", label="nav_nav1d")
    mock_parse.assert_called_once()
    # Verify metadata passed
    args, kwargs = mock_parse.call_args
    # Update expected metadata to include query info
    expected_meta = {
        "ibkr_report_type": NavReportType.NAV_1D,
        "ibkr_query_id": "1001",
        "ibkr_query_name": "NAV1D"
    }
    assert kwargs["metadata"] == expected_meta

@patch("app.services.ibkr_service.get_system_config")
@patch("app.services.ibkr_service.save_sync_status")
def test_fetch_fail_no_query_id(mock_save, mock_get_config, mock_config):
    mock_get_config.return_value = mock_config
    # NAV_30D is not in config
    with pytest.raises(Exception) as excinfo:
        fetch_and_store_nav_report(NavReportType.NAV_30D)
    assert "No Query ID configured" in str(excinfo.value)

# --- API Tests ---

from fastapi import BackgroundTasks

@patch("app.api.routes.MongoClient")
@patch("app.services.portfolio_analysis.MongoClient")
@patch("app.services.ibkr_service.fetch_and_store_nav_report") # Mock the service call
def test_get_nav_report_endpoint_triggers_fetch(mock_fetch_service, mock_mongo_analysis, mock_mongo_route, mock_config):
    # Mock DB
    mock_db = MagicMock()
    mock_mongo_route.return_value.get_default_database.return_value = mock_db
    mock_mongo_analysis.return_value.get_default_database.return_value = mock_db

    # Simulate MISSING data (find_one returns None)
    mock_db.ibkr_nav_history.find_one.return_value = None
    mock_db.ibkr_raw_flex_reports.find_one.return_value = None
    
    # Use MagicMock for BackgroundTasks to avoid any runtime overhead/logic
    bg_tasks = MagicMock()
    user = MagicMock()
    
    response = get_nav_report_endpoint(NavReportType.NAV_1D, bg_tasks, user)
    
    assert response["status"] == "fetching"
    # Verify task added
    bg_tasks.add_task.assert_called_once()
    args, kwargs = bg_tasks.add_task.call_args
    # First arg should be the function
    assert args[0] == fetch_and_store_nav_report
    # Second arg should be the report type
    assert args[1] == NavReportType.NAV_1D

@patch("app.api.routes.MongoClient")
@patch("app.services.portfolio_analysis.MongoClient")
def test_get_nav_report_endpoint_returns_data(mock_mongo_analysis, mock_mongo_route):
    # Mock DB
    mock_db = MagicMock()
    mock_mongo_route.return_value.get_default_database.return_value = mock_db
    # Also mock analysis DB since it is called first
    mock_mongo_analysis.return_value.get_default_database.return_value = mock_db
    
    # Simulate EXISTING data
    mock_db.ibkr_nav_history.find_one.return_value = {
         "_report_date": datetime.utcnow().strftime("%Y-%m-%d"),
         "ibkr_report_type": "NAV1D"
    }
    # Simulate Aggregation Result for get_report_stats
    mock_db.ibkr_nav_history.aggregate.return_value = [{
        "total_start": 100,
        "total_end": 110,
        "first_start": 100,
        "last_end": 110
    }]
    
    mock_db.ibkr_raw_flex_reports.find_one.return_value = {
        "_ingested_at": datetime.utcnow(),
        "ibkr_report_type": "Nav1D"
    }
    
    bg_tasks = MagicMock()
    user = MagicMock()
    
    response = get_nav_report_endpoint(NavReportType.NAV_1D, bg_tasks, user)
    
    assert response["status"] == "available"
    bg_tasks.add_task.assert_not_called()


@patch("app.api.routes.get_ibkr_tws_service")
def test_get_portfolio_live_status_returns_tws_snapshot(mock_get_service):
    mock_get_service.return_value.get_live_status.return_value = {
        "connected": True,
        "last_position_update": "2026-03-30T18:22:00+00:00",
        "position_count": 3,
        "tws_enabled": True,
    }
    user = MagicMock(role="portfolio")

    response = asyncio.run(get_portfolio_live_status(user))

    assert response["connected"] is True
    assert response["position_count"] == 3
    assert response["tws_enabled"] is True


@patch("app.services.portfolio_analysis.get_latest_live_nav_snapshot")
def test_get_portfolio_live_nav_returns_latest_snapshot(mock_get_snapshot):
    mock_get_snapshot.return_value = {
        "timestamp": datetime(2026, 3, 30, 18, 25),
        "total_nav": 25000.5,
        "unrealized_pnl": 125.0,
        "realized_pnl": 10.0,
        "accounts": ["DU123456"],
        "source": "tws",
        "last_tws_update": datetime(2026, 3, 30, 18, 25),
    }
    user = MagicMock(role="portfolio")

    response = asyncio.run(get_portfolio_live_nav(user))

    assert response["total_nav"] == 25000.5
    assert response["accounts"] == ["DU123456"]
    assert response["source"] == "tws"


@patch("app.services.portfolio_analysis.get_nav_history_stats")
def test_get_portfolio_stats_exposes_data_source_and_last_updated(mock_get_stats):
    mock_get_stats.return_value = {
        "current_nav": 1000,
        "history": [],
        "data_source": "tws_live",
        "last_updated": "2026-03-30T18:25:00+00:00",
    }
    user = MagicMock(role="portfolio")

    response = asyncio.run(get_portfolio_stats(user))

    assert response["data_source"] == "tws_live"
    assert response["last_updated"] == "2026-03-30T18:25:00+00:00"
