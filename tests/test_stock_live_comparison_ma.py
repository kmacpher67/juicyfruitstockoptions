import pandas as pd
from stock_live_comparison import StockLiveComparison
import pytest

def make_hist(prices):
    return pd.DataFrame({'Close': prices})

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

def test_get_highlight_status_green():
    comp = StockLiveComparison([])
    assert comp.get_highlight_status(90, 100, threshold=0.05) == 'green'  # 10% below

def test_get_highlight_status_red():
    comp = StockLiveComparison([])
    assert comp.get_highlight_status(110, 100, threshold=0.05) == 'red'  # 10% above

def test_get_highlight_status_none():
    comp = StockLiveComparison([])
    assert comp.get_highlight_status(102, 100, threshold=0.05) is None  # within 2%
    assert comp.get_highlight_status(98, 100, threshold=0.05) is None
    assert comp.get_highlight_status(None, 100, threshold=0.05) is None
    assert comp.get_highlight_status(100, None, threshold=0.05) is None

def test_fetch_ticker_record_adds_ma_and_highlight():
    comp = StockLiveComparison([])
    hist = make_hist([100]*200)
    info = {'regularMarketPrice': 90}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert 'MA_30' in record and 'MA_200' in record
    assert 'MA_30_highlight' in record and record['MA_30_highlight'] == 'green'
    info = {'regularMarketPrice': 110}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert record['MA_30_highlight'] == 'red'
    info = {'regularMarketPrice': 100}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert record['MA_30_highlight'] is None
