import pytest
from app.services.risk_service import RiskService

class TestRiskService:
    
    def test_check_impatience_high_rsi(self):
        """Test risk warning for high RSI (Long Call Impatience)."""
        data = {
            "Ticker": "NVDA",
            "RSI_14": 80,             # > 75
            "Current Price": 100,
            "EMA_20": 90,
            "ATR_14": 2,
            "Annual Yield Call Prem": 10,
            "Annual Yield Put Prem": 5
        }
        
        warnings = RiskService.analyze_risk(data)
        
        # Should trigger "Impatience" warning
        assert any(w["type"] == "Impatience" for w in warnings)
        assert len(warnings) >= 1

    def test_check_trend_extension(self):
        """Test risk warning for price far above SMA (Trend Extension)."""
        # Price = 120. EMA_20 = 100. ATR = 2.
        # Threshold = EMA + 3*ATR = 100 + 6 = 106.
        # Price 120 > 106. Should trigger warning.
        data = {
            "Ticker": "TSLA",
            "RSI_14": 60,
            "Current Price": 120,
            "EMA_20": 100,
            "ATR_14": 2,
            "Annual Yield Call Prem": 10,
            "Annual Yield Put Prem": 5
        }
        
        warnings = RiskService.analyze_risk(data)
        
        assert any(w["type"] == "Trend Extension" for w in warnings)

    def test_check_liquidity_wide_spread(self):
        """Test risk warning for wide option spreads."""
        # This check depends on if we have spread data. 
        # Assuming we pass 'Spread Width %' if available, or calculate it.
        # Let's say we pass raw 'Call Bid' and 'Call Ask'.
        # For V1, we might just look at "Volume" or "Market Cap" as proxy if spread unavailable,
        # but Plan said "Spread > 10%".
        # Let's assume the data object has "Average Spread %" populated by Scanner/LiveComparison.
        
        data = {
            "Ticker": "ILLIQ",
            "RSI_14": 50,
            "Current Price": 100,
            "EMA_20": 100,
            "ATR_14": 2,
            "Option Spread Pct": 0.15, # 15% spread
        }
        
        warnings = RiskService.analyze_risk(data)
        assert any(w["type"] == "Liquidity" for w in warnings)

    def test_no_risks(self):
        """Test clean data with no risks."""
        data = {
            "Ticker": "SAFE",
            "RSI_14": 50,
            "Current Price": 100,
            "EMA_20": 98,
            "ATR_14": 2,
            "Option Spread Pct": 0.01
        }
        
        warnings = RiskService.analyze_risk(data)
        assert len(warnings) == 0
