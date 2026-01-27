import pandas as pd
import pytest
from stock_live_comparison import StockLiveComparison

def test_calculate_ema():
    # Test EMA with a simple series
    prices = pd.Series([10, 11, 12, 13, 14, 15] * 5) # enough data
    ema = StockLiveComparison.calculate_ema(prices, span=20)
    assert ema is not None
    expected = round(prices.ewm(span=20, adjust=False).mean().iloc[-1], 2)
    assert ema == expected

def test_calculate_hma():
    # Test HMA
    # Create a linear trend
    prices = pd.Series(range(10, 50)) # 40 points
    comp = StockLiveComparison([])
    hma = comp.calculate_hma(prices, window=20)
    assert hma is not None
    # HMA on linear data should be very close to the last price (49)
    assert 48 < hma < 50 

def test_calculate_tsmom():
    # Test TSMOM (Return)
    # Lookback 60 days
    # Price t=0 is 100, t=60 is 110. Return should be (110/100) - 1 = 0.10
    prices = [100] * 70
    prices[-1] = 110
    series = pd.Series(prices)
    
    # Check logic: current = series.iloc[-1] (index 69)
    # lookback=60. -(60+1) = -61.
    # iloc[-61] is index 9 (100)
    
    tsmom = StockLiveComparison.calculate_tsmom(series, lookback=60)
    assert tsmom == 0.1000

    # Test negative
    prices[-1] = 90
    series = pd.Series(prices)
    tsmom = StockLiveComparison.calculate_tsmom(series, lookback=60)
    assert tsmom == -0.1000
    
    # Test shorter series returns None
    short_series = pd.Series([100] * 50)
    tsmom_slk = StockLiveComparison.calculate_tsmom(short_series, lookback=60)
    assert tsmom_slk is None
