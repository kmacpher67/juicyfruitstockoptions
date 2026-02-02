import pandas as pd
from stock_live_comparison import StockLiveComparison
import pytest

def make_hist(prices):
    df = pd.DataFrame({'Close': prices})
    df['High'] = prices
    df['Low'] = prices
    df['Open'] = prices
    df['Volume'] = 1000
    df['Date'] = pd.date_range("2023-01-01", periods=len(prices))
    return df

def test_calculate_moving_averages_positive():
    hist = make_hist([1]*200)
    comp = StockLiveComparison([])
    ma = comp.calculate_moving_averages(hist, windows=(30, 60, 120, 200))
    assert ma['MA_30'] == 1
    assert ma['MA_60'] == 1
    assert ma['MA_120'] == 1
    assert ma['MA_200'] == 1

def test_calculate_moving_averages_negative():
    hist = make_hist([1]*10)
    comp = StockLiveComparison([])
    ma = comp.calculate_moving_averages(hist, windows=(30, 60, 120))
    assert ma['MA_30'] is None
    assert ma['MA_60'] is None
    assert ma['MA_120'] is None

def test_calculate_ma_delta():
    comp = StockLiveComparison([])
    # Avg 100, Price 90 -> (90-100)/100 = -0.10
    assert comp.calculate_ma_delta(90, 100) == -0.10
    # Avg 100, Price 110 -> 0.10
    assert comp.calculate_ma_delta(110, 100) == 0.10
    # None cases
    assert comp.calculate_ma_delta(None, 100) is None
    assert comp.calculate_ma_delta(100, None) is None
    assert comp.calculate_ma_delta(100, 0) is None

def test_fetch_ticker_record_adds_ma_and_highlight(monkeypatch):
    comp = StockLiveComparison([])
    hist = make_hist([100]*200)
    info = {
        'regularMarketPrice': 90, 
        'marketCap': 1e12, 
        'trailingPE': 20, 
        'dividendYield': 0.02,
        'targetMeanPrice': 100,
        'exDividendDate': None
    }
    
    # Mock option methods to avoid chain issues
    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args: (None, None))
    
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert 'MA_30' in record and 'MA_200' in record
    assert 'MA_30_highlight' in record
    # MA should be 100, Price 90, so delta is -0.10
    assert record['MA_30_highlight'] == -0.10

    info['regularMarketPrice'] = 110
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    # MA 100, Price 110, delta 0.10
    assert record['MA_30_highlight'] == 0.10

    info['regularMarketPrice'] = 100
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    # MA 100, Price 100, delta 0.0
    assert record['MA_30_highlight'] == 0.0
