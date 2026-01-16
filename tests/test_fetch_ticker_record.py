import pandas as pd
from stock_live_comparison import StockLiveComparison

def test_fetch_ticker_record_ma_and_highlight():
    comp = StockLiveComparison([])
    hist = pd.DataFrame({'Close': [100]*200})
    info = {'regularMarketPrice': 90}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert record['MA_30'] == 100
    assert record['MA_60'] == 100
    assert record['MA_120'] == 100
    assert record['MA_200'] == 100
    assert record['MA_30_highlight'] == 'green'
    info = {'regularMarketPrice': 110}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert record['MA_30_highlight'] == 'red'
    info = {'regularMarketPrice': 100}
    record = comp.fetch_ticker_record('TST', info, hist, chain=None)
    assert record['MA_30_highlight'] is None

def test_fetch_ticker_record_handles_missing_hist():
    comp = StockLiveComparison([])
    info = {'regularMarketPrice': 100}
    record = comp.fetch_ticker_record('TST', info, None, chain=None)
    assert record['MA_30'] is None
    assert record['MA_30_highlight'] is None
