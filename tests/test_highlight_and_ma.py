import pytest
from stock_live_comparison import StockLiveComparison
import pandas as pd

def test_get_highlight_status_green():
    comp = StockLiveComparison([], highlight_threshold=0.05)
    assert comp.get_highlight_status(95, 100) == 'green'
    assert comp.get_highlight_status(90, 100) == 'green'

def test_get_highlight_status_red():
    comp = StockLiveComparison([], highlight_threshold=0.05)
    assert comp.get_highlight_status(105, 100) == 'red'
    assert comp.get_highlight_status(110, 100) == 'red'

def test_get_highlight_status_none():
    comp = StockLiveComparison([], highlight_threshold=0.05)
    assert comp.get_highlight_status(102, 100) is None
    assert comp.get_highlight_status(98, 100) is None
    assert comp.get_highlight_status(None, 100) is None
    assert comp.get_highlight_status(100, None) is None

def test_calculate_moving_averages_full():
    comp = StockLiveComparison([])
    hist = pd.DataFrame({'Close': [1]*200})
    ma = comp.calculate_moving_averages(hist, windows=(30, 60, 180, 200))
    assert ma['MA_30'] == 1
    assert ma['MA_60'] == 1
    assert ma['MA_180'] == 1
    assert ma['MA_200'] == 1

def test_calculate_moving_averages_partial():
    comp = StockLiveComparison([])
    hist = pd.DataFrame({'Close': [1]*10})
    ma = comp.calculate_moving_averages(hist, windows=(30, 60))
    assert ma['MA_30'] is None
    assert ma['MA_60'] is None
