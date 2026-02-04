
import os
import pytest
import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta
from app.services.dividend_scanner import DividendScanner

@pytest.fixture
def mock_settings():
    with patch("app.services.dividend_scanner.settings") as mock_settings:
        mock_settings.MONGO_URI = "mongodb://mock:27017"
        mock_settings.CALENDAR_LOOKAHEAD_DAYS = 30
        yield mock_settings

# Mock os.path and file operations to avoid permission issues
@pytest.fixture
def mock_fs():
    with patch("app.services.dividend_scanner.os") as mock_os:
        mock_os.path.exists.return_value = False
        mock_os.path.join.side_effect = os.path.join
        yield mock_os

@pytest.fixture
def mock_open_file():
    m = mock_open()
    with patch("app.services.dividend_scanner.open", m):
        yield m

@pytest.fixture
def mock_mongo():
    with patch("pymongo.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        yield mock_db

@pytest.fixture
def mock_news_service():
    with patch("app.services.dividend_scanner.NewsService") as MockService:
        service_instance = MockService.return_value
        yield service_instance

@pytest.fixture
def mock_dependencies():
    with patch("app.services.dividend_scanner.OpportunityService") as MockOpp, \
         patch("app.services.dividend_scanner.SignalService") as MockSig, \
         patch("app.services.dividend_scanner.RollService") as MockRoll:
        yield (MockOpp, MockSig, MockRoll)

@pytest.fixture
def mock_yfinance():
    with patch("app.services.dividend_scanner.yf") as mock_yf:
        yield mock_yf

def test_generate_corporate_events_calendar_logic(mock_mongo, mock_news_service, mock_yfinance, mock_settings, mock_dependencies, mock_fs, mock_open_file):
    """
    Verify corporate events logic with full dependency mocking.
    """
    scanner = DividendScanner()
    
    # --- Setup Mocks ---
    
    # 1. Mock Holdings Check (Found 1 symbol 'AAPL')
    mock_mongo.ibkr_holdings.find_one.return_value = {"snapshot_id": "snap_1", "date": datetime.utcnow()}
    mock_mongo.ibkr_holdings.find.return_value = [{"symbol": "AAPL"}]
    
    # 2. Mock yfinance Ticker Data
    mock_ticker = MagicMock()
    mock_yfinance.Ticker.return_value = mock_ticker
    
    # Ex-Div Data
    mock_ticker.info = {
        "exDividendDate": (datetime.utcnow() + timedelta(days=5)).timestamp(),
        "dividendRate": 0.96
    }
    
    # Earnings Data (Calendar)
    earnings_date = datetime.utcnow() + timedelta(days=3)
    mock_ticker.calendar = {"Earnings Date": [earnings_date]} # Simple dict structure
    
    # 3. Mock DB Persistence (Upsert)
    # _persist_event calls update_one
    
    # 4. Mock DB Query for ICS Generation
    # Return 2 events: One Ex-Div, One Earnings
    mock_events = [
        {
            "ticker": "AAPL",
            "event_type": "Ex-Dividend",
            "date": datetime.utcnow() + timedelta(days=5),
            "details": "Rate: 0.96"
        },
        {
            "ticker": "AAPL",
            "event_type": "Earnings",
            "date": earnings_date,
            "details": "Estimated Earnings"
        }
    ]
    mock_mongo.corporate_events.find.return_value = mock_events
    
    # 5. Mock News (Bullish Article)
    mock_article = MagicMock()
    mock_article.title = "AAPL Hits All Time High"
    mock_article.sentiment_score = 0.8
    mock_article.logic = "Positive Momentum"
    mock_article.url = "http://news.com/aapl"
    mock_news_service.fetch_news_for_ticker.return_value = [mock_article]
    
    # --- Execute ---
    ics_path = scanner.generate_corporate_events_calendar()
    
    # --- Verify ---
    
    # 1. Persistence Called?
    assert mock_mongo.corporate_events.update_one.call_count >= 2
    
    # 2. News Service Called?
    # Both events are within 14 days, so news should be fetched.
    mock_news_service.fetch_news_for_ticker.assert_called_with("AAPL")
    
    # 3. Verify ICS Content (via Mock Write)
    mock_open_file.assert_called()
    handle = mock_open_file()
    
    # Combine all writes to check content
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    
    # Check Ex-Div Link
    assert "Link: https://finance.yahoo.com/quote/AAPL" in written_content
    
    # Check Earnings (News Integration)
    assert "Headline: AAPL Hits All Time High" in written_content
    assert "Link: http://news.com/aapl" in written_content
    assert "Sentiment: 0.8" in written_content
        
    print(f"Verified ICS Content via Mock")
