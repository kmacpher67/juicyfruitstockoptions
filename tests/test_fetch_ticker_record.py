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

    record = comp.fetch_ticker_record('TST', info, None, mock_chain)
    
    assert record['MA_30'] is None
    assert record['MA_30_highlight'] is None
