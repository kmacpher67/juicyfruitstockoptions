from datetime import datetime
import pytest
from stock_live_comparison import StockLiveComparison

def test_generate_yf_option_url_format():
    # Test with a specific date
    ticker = "AAPL"
    # Format: YYYY-MM-DD
    # Unix timestamp for 2025-01-17 (UTC) should be used in the URL.
    # Note: Yahoo Finance generally uses unix timestamp for the date at midnight or similar.
    # Let's verify what the method does once implemented. 
    # For now, we expect the method to take a ticker and a date string (YYYY-MM-DD).
    
    date_str = "2025-01-17"
    # Calculate expected timestamp: 2025-01-17 00:00:00 UTC
    from datetime import timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    url = StockLiveComparison.generate_yf_option_url(ticker, date_str)
    
    expected_timestamp = int(dt.timestamp())
    
    assert f"finance.yahoo.com/quote/{ticker}/options" in url
    assert f"straddle=true" in url
    assert f"date={expected_timestamp}" in url 

def test_generate_yf_option_url_structure():
    ticker = "MSFT"
    date_str = "2026-06-18"
    from datetime import timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    expected_ts = int(dt.timestamp())
    
    url = StockLiveComparison.generate_yf_option_url(ticker, date_str)
    
    assert url.startswith(f"https://finance.yahoo.com/quote/{ticker}/options")
    assert "?date=" in url
    assert "&straddle=true" in url
    assert str(expected_ts) in url

def test_generate_yf_option_url_invalid_date():
    # Helper should probably handle or raise, but for now let's manually assume consistent input
    # If None is passed, maybe return None or just base URL?
    url = StockLiveComparison.generate_yf_option_url("AAPL", None)
    assert url is None

