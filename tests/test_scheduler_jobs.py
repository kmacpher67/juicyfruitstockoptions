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

