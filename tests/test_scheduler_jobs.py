from unittest.mock import MagicMock, patch
import app.scheduler.jobs as jobs

@patch('app.scheduler.jobs.DividendScanner')
@patch('app.scheduler.jobs.MongoClient')
def test_run_dividend_scan_wrapper_cleans_symbols(MockMongoClient, MockDividendScanner):
    """
    Verify that the dividend scan wrapper correctly extracts underlying
    stock symbols from option contracts before passing them to the scanner.
    """
    # 1. Mock the database to return holdings with mixed symbol types
    mock_db = MagicMock()
    mock_db.ibkr_holdings.find_one.return_value = {"date": "2026-04-02"} # Simulate finding a recent snapshot
    mock_db.ibkr_holdings.find.return_value = [
        {
            "symbol": "AAPL",
            "secType": "STK",
            "asset_class": "STK",
            "underlying_symbol": None,
        },
        {
            "symbol": "MSFT  260419C00500000",
            "secType": "OPT",
            "asset_class": "OPT",
            "underlying_symbol": "MSFT", # Test with explicit underlying
        },
        {
            "symbol": "GOOG  260419P00300000", # Test parsing from symbol string
            "secType": "OPT",
            "asset_class": "OPT",
            "underlying_symbol": None,
        },
        {
            "symbol": "NVDA", # Test a simple stock symbol among options
            "secType": "STK",
            "asset_class": "STK",
            "underlying_symbol": None,
        }
    ]
    
    # Configure the MongoClient mock that is passed into the test
    mock_client_instance = MockMongoClient.return_value
    mock_client_instance.get_default_database.return_value = mock_db
    
    # Configure the DividendScanner mock
    mock_scanner_instance = MockDividendScanner.return_value
    
    # 2. Call the actual job function
    jobs.run_dividend_scan_wrapper()
    
    # 3. Assert the scanner was called with cleaned symbols
    mock_scanner_instance.scan_dividend_capture_opportunities.assert_called_once()
    
    # Get the arguments passed to the mocked method
    args, kwargs = mock_scanner_instance.scan_dividend_capture_opportunities.call_args
    # The 'tickers' argument is the first positional argument
    called_with_tickers = args[0]
    # We expect {'AAPL', 'MSFT', 'GOOG', 'NVDA'}
    assert len(called_with_tickers) == 4
    assert set(called_with_tickers) == {"AAPL", "MSFT", "GOOG", "NVDA"}


def test_run_price_history_retention_cleanup_deletes_rows_older_than_cutoff():
    mock_db = MagicMock()
    mock_db.system_config.find_one.return_value = {"_id": "data_freshness_config", "price_history_retention_days": 365}
    mock_db.instrument_price_history.delete_many.return_value.deleted_count = 123

    with patch("app.scheduler.jobs._get_db", return_value=mock_db):
        jobs.run_price_history_retention_cleanup()

    call_query = mock_db.instrument_price_history.delete_many.call_args[0][0]
    assert "timestamp" in call_query
    assert "$lt" in call_query["timestamp"]
    assert isinstance(call_query["timestamp"]["$lt"], str)
    assert len(call_query["timestamp"]["$lt"]) >= 19


def test_start_scheduler_registers_price_history_retention_job():
    mock_scheduler = MagicMock()
    with patch("app.scheduler.jobs.scheduler", mock_scheduler), patch("app.scheduler.jobs.tag_existing_flex_sync_sources"), patch(
        "app.scheduler.jobs.get_schedule_config", return_value={"hour": 10, "minute": 0}
    ):
        jobs.start_scheduler()

    job_ids = [call.kwargs.get("id") for call in mock_scheduler.add_job.call_args_list]
    assert "instrument_price_history_retention_daily" in job_ids


def test_run_stock_live_comparison_scheduled_runs_single_job_when_sharding_disabled():
    with patch(
        "app.scheduler.jobs._get_stock_analysis_scheduler_config",
        return_value={"scheduler_sharding_enabled": False, "scheduler_shard_size": 2, "scheduler_shard_pause_sec": 0.0},
    ), patch("app.scheduler.jobs.run_stock_live_comparison", return_value={"status": "success"}) as mock_run:
        result = jobs.run_stock_live_comparison_scheduled()

    assert result["status"] == "success"
    mock_run.assert_called_once_with(trigger="scheduled")


def test_run_stock_live_comparison_scheduled_shards_tickers_and_paces_between_shards():
    with patch(
        "app.scheduler.jobs._get_stock_analysis_scheduler_config",
        return_value={"scheduler_sharding_enabled": True, "scheduler_shard_size": 2, "scheduler_shard_pause_sec": 0.01},
    ), patch("app.scheduler.jobs.run_stock_live_comparison", return_value={"status": "success", "file": "f.xlsx"}) as mock_run, patch(
        "app.scheduler.jobs.time.sleep"
    ) as mock_sleep, patch("app.services.ticker_discovery.discover_and_track_tickers"), patch(
        "stock_live_comparison.StockLiveComparison.get_default_tickers",
        return_value=["AAPL", "MSFT", "NVDA", "AMD", "GOOG"],
    ):
        result = jobs.run_stock_live_comparison_scheduled()

    assert result["status"] == "success"
    assert result["mode"] == "sharded"
    assert result["shard_count"] == 3
    assert mock_run.call_count == 3
    assert mock_run.call_args_list[0].kwargs == {"tickers": ["AAPL", "MSFT"], "trigger": "scheduled"}
    assert mock_run.call_args_list[1].kwargs == {"tickers": ["NVDA", "AMD"], "trigger": "scheduled"}
    assert mock_run.call_args_list[2].kwargs == {"tickers": ["GOOG"], "trigger": "scheduled"}
    assert mock_sleep.call_count == 2


def test_start_scheduler_registers_stock_comparison_wrapper_job():
    mock_scheduler = MagicMock()
    with patch("app.scheduler.jobs.scheduler", mock_scheduler), patch("app.scheduler.jobs.tag_existing_flex_sync_sources"), patch(
        "app.scheduler.jobs.get_schedule_config", return_value={"hour": 10, "minute": 0}
    ):
        jobs.start_scheduler()

    call = next(c for c in mock_scheduler.add_job.call_args_list if c.kwargs.get("id") == "stock_comparison_job")
    assert call.args[0] is jobs.run_stock_live_comparison_scheduled
