import pandas as pd
import pytest
from stock_live_comparison import StockLiveComparison

@pytest.fixture
def mock_chain():
    """We don't need a real chain if we mock the methods that use it."""
    return None

def test_fetch_ticker_record_ma_and_highlight(mock_chain, monkeypatch):
    comp = StockLiveComparison([])
    hist = pd.DataFrame({
        'Close': [100]*200,
        'High': [100]*200,
        'Low': [100]*200,
        'Open': [100]*200,
        'Volume': [1000]*200,
        'Date': pd.date_range("2023-01-01", periods=200)
    })
    info = {
        'regularMarketPrice': 90, 
        'marketCap': 1e12, 
        'trailingPE': 20, 
        'dividendYield': 0.02,
        'targetMeanPrice': 100,
        'exDividendDate': None
    }
    
    # Mock the OTM methods to avoid using chain
    # Mock the OTM methods to avoid using chain
    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args: (None, None, None))
    
    record = comp.fetch_ticker_record('TST', info, hist, mock_chain)
    
    assert 'MA_30' in record and 'MA_200' in record
    assert 'MA_30_highlight' in record
    # MA should be 100, Price 90, so delta is -0.10
    assert record['MA_30_highlight'] == -0.10

def test_fetch_ticker_record_handles_missing_hist(mock_chain, monkeypatch):
    comp = StockLiveComparison([])
    info = {'regularMarketPrice': 100}

    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args: (None, None, None))

    record = comp.fetch_ticker_record('TST', info, None, mock_chain)

    assert record['MA_30'] is None
    assert record['MA_30_highlight'] is None


# --- Profile sub-document tests ---

class MockChainWithNews:
    """Minimal yfinance Ticker-like object with .news attribute."""
    def __init__(self, news=None):
        self.news = news or []


def _base_hist():
    return pd.DataFrame({
        'Close': [100] * 200,
        'High': [100] * 200,
        'Low': [100] * 200,
        'Open': [100] * 200,
        'Volume': [1000] * 200,
        'Date': pd.date_range("2023-01-01", periods=200),
    })


def _base_info():
    return {
        'regularMarketPrice': 100,
        'sector': 'Technology',
        'industry': 'Semiconductors',
        'longBusinessSummary': 'A great company.',
        'quoteType': 'EQUITY',
        'category': None,
        'exchange': 'NMS',
        'country': 'United States',
        'fullTimeEmployees': 10000,
        'website': 'https://example.com',
        'recommendationKey': 'buy',
        'numberOfAnalystOpinions': 30,
        'beta': 1.5,
        'forwardPE': 25.0,
        'priceToBook': 5.0,
        'returnOnEquity': 0.35,
        'debtToEquity': 0.5,
        'earningsGrowth': 0.20,
        'revenueGrowth': 0.15,
    }


def test_fetch_ticker_record_includes_profile(monkeypatch):
    comp = StockLiveComparison([])
    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args: (None, None, None))

    chain = MockChainWithNews(news=[
        {'title': 'Big news', 'publisher': 'Reuters', 'link': 'http://x.com', 'providerPublishTime': 1700000000}
    ])
    record = comp.fetch_ticker_record('TST', _base_info(), _base_hist(), chain)

    assert 'profile' in record
    p = record['profile']
    assert p['sector'] == 'Technology'
    assert p['industry'] == 'Semiconductors'
    assert p['description'] == 'A great company.'
    assert p['recommendation'] == 'buy'
    assert p['beta'] == 1.5
    assert len(p['news']) == 1
    assert p['news'][0]['title'] == 'Big news'
    assert p['news'][0]['publisher'] == 'Reuters'


def test_fetch_ticker_record_profile_news_empty_on_exception(monkeypatch):
    """When chain.news raises, profile is still returned with empty news list."""
    comp = StockLiveComparison([])
    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args: (None, None, None))

    class BrokenChain:
        @property
        def news(self):
            raise RuntimeError("yfinance error")

    record = comp.fetch_ticker_record('TST', _base_info(), _base_hist(), BrokenChain())

    assert 'profile' in record
    assert record['profile']['news'] == []
    assert record['profile']['sector'] == 'Technology'


def test_fetch_ticker_record_profile_news_capped_at_5(monkeypatch):
    comp = StockLiveComparison([])
    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args: (None, None, None))

    news = [
        {'title': f'News {i}', 'publisher': 'P', 'link': 'http://x.com', 'providerPublishTime': 1700000000}
        for i in range(10)
    ]
    chain = MockChainWithNews(news=news)
    record = comp.fetch_ticker_record('TST', _base_info(), _base_hist(), chain)

    assert len(record['profile']['news']) == 5
