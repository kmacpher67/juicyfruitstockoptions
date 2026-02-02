import pytest
import pandas as pd
import numpy as np
from stock_live_comparison import StockLiveComparison

class TestStockIndicators:
    
    def test_calculate_rsi_simple_gain(self):
        """Test RSI calculation with a simple upward trend."""
        # Create a series that goes up consistently
        data = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        series = pd.Series(data)
        
        rsi = StockLiveComparison.calculate_rsi(series, period=14)
        
        # In a pure upward trend (no losses), RSI should be 100
        # Formula: RS = AvgGain / AvgLoss. If AvgLoss is 0, RSI is 100.
        assert rsi == 100.0

    def test_calculate_rsi_simple_loss(self):
        """Test RSI calculation with a simple downward trend."""
        # Create a series that goes down consistently
        data = [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10]
        series = pd.Series(data)
        
        rsi = StockLiveComparison.calculate_rsi(series, period=14)
        
        # In a pure downward trend (no gains), RSI should be 0
        assert rsi == 0.0

    def test_calculate_rsi_oscillation(self):
        """Test RSI with mixed data."""
        # 15 data points
        # Changes: +1, -1, +1, -1 ...
        data = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10]
        series = pd.Series(data)
        
        rsi = StockLiveComparison.calculate_rsi(series, period=14)
        
        # Avg Gain should be approx equal to Avg Loss, so RS ~ 1, RSI ~ 50
        # First diff is NaN.
        # Gains: 1, 0, 1, 0...
        # Losses: 0, 1, 0, 1...
        # Over 14 periods, we have 7 gains of 1, 7 losses of 1.
        # AvgGain = 0.5, AvgLoss = 0.5. RS = 1. RSI = 100 - (100/2) = 50.
        assert 49.0 <= rsi <= 51.0

    def test_calculate_atr_steady(self):
        """Test ATR with steady range."""
        # High-Low is always 2. Close is steady.
        highs = [12] * 20
        lows = [10] * 20
        closes = [11] * 20
        
        h_series = pd.Series(highs)
        l_series = pd.Series(lows)
        c_series = pd.Series(closes)
        
        atr = StockLiveComparison.calculate_atr(h_series, l_series, c_series, period=14)
        
        # TR is always 2 (12-10=2, |12-11|=1, |10-11|=1). Max is 2.
        # Average of 2s is 2.
        assert atr == 2.0

    def test_calculate_atr_gap(self):
        """Test ATR with a gap up (True Range should include gap)."""
        # Close at 10. Next day High 15, Low 14.
        # H-L = 1.
        # H-Cp = 15-10 = 5.
        # L-Cp = 14-10 = 4.
        # Max is 5.
        
        highs = [10] * 15 + [15]
        lows = [9] * 15 + [14]
        closes = [9.5] * 15 + [14.5]
        # modify one close to create the gap
        closes[14] = 10
        
        h_series = pd.Series(highs)
        l_series = pd.Series(lows)
        c_series = pd.Series(closes)
        
        atr = StockLiveComparison.calculate_atr(h_series, l_series, c_series, period=14)
        
        # Just verifying it returns a number and doesn't crash
        assert atr is not None
        assert atr > 0

    def test_calculate_tsmom(self):
        """Test TSMOM calculation."""
        # Price doubles over lookback
        data = [10] * 70
        data[-1] = 20 # Current
        
        series = pd.Series(data)
        
        # Lookback 60. 
        # Index -1 is 20. Index -(60+1) = -61 is 10.
        # (20/10) - 1 = 1.0 (100%)
        tsmom = StockLiveComparison.calculate_tsmom(series, lookback=60)
        assert tsmom == 1.0

    def test_insufficient_data(self):
        """Verify None is returned for insufficient data."""
        series = pd.Series([1, 2, 3])
        
        assert StockLiveComparison.calculate_rsi(series, period=14) is None
        assert StockLiveComparison.calculate_tsmom(series, lookback=60) is None
