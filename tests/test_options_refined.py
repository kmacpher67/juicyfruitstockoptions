import pytest
from app.services.options_analysis import OptionsAnalyzer

@pytest.fixture
def mock_holdings():
    return [
        # 1. 200 Shares of AAPL (Uncovered)
        {"symbol": "AAPL", "asset_class": "STK", "quantity": 200, "underlying_symbol": "AAPL"},
        
        # 2. 100 Shares of NVDA (Covered by 1 call)
        {"symbol": "NVDA", "asset_class": "STK", "quantity": 100, "underlying_symbol": "NVDA"},
        {"symbol": "NVDA 250117C00150000", "asset_class": "OPT", "quantity": -1, "multiplier": 100, "underlying": "NVDA"},
        
        # 3. 200 Shares of TSLA (Negative Trend)
        {"symbol": "TSLA", "asset_class": "STK", "quantity": 200, "underlying_symbol": "TSLA"},
    ]

@pytest.fixture
def mock_market_data():
    return {
        "AAPL": {
            "Ticker": "AAPL",
            "Current Price": 150.0,
            "1D % Change": "+1.5%", # Positive Trend
            "TSMOM_60": 10.0,      # Positive Momentum
            "Call/Put Skew": 1.2   # High Skew
        },
        "TSLA": {
            "Ticker": "TSLA",
            "Current Price": 200.0,
            "1D % Change": "-2.0%", # Negative Trend
            "TSMOM_60": -5.0,
            "Call/Put Skew": 0.8
        },
        "NVDA": {
             "Ticker": "NVDA",
             "1D % Change": "+0.5%",
             "TSMOM_60": 5.0,
             "Call/Put Skew": 0.9 
        }
    }

def test_trend_filtering(mock_holdings, mock_market_data):
    """
    Verify checks:
    - AAPL: UP trend -> Should Alert.
    - TSLA: DOWN trend -> Should NOT Alert (even though it has 200 uncovered shares).
    """
    analyzer = OptionsAnalyzer(mock_holdings, market_data=mock_market_data)
    alerts = analyzer.analyze_coverage()
    
    symbols = [a['symbol'] for a in alerts]
    
    assert "AAPL" in symbols, "AAPL should be alerted (Positive Trend)"
    assert "TSLA" not in symbols, "TSLA should be skipped (Negative Trend)"

def test_strength_score(mock_holdings, mock_market_data):
    """
    Verify Score Calculation for AAPL.
    TSMOM > 0 (+40)
    1D > 0 (+30)
    Skew > 1.0 (+30)
    Total should be 100.
    """
    analyzer = OptionsAnalyzer(mock_holdings, market_data=mock_market_data)
    alerts = analyzer.analyze_coverage()
    
    aapl_alert = next(a for a in alerts if a['symbol'] == "AAPL")
    print(f"AAPL Score: {aapl_alert['score']}")
    
    assert aapl_alert['score'] == 70
    
def test_missing_data_defaults(mock_holdings):
    """
    If no market data, assume 0 change -> No Alert (Conservative).
    """
    analyzer = OptionsAnalyzer(mock_holdings, market_data={}) # Empty data
    alerts = analyzer.analyze_coverage()
    
    assert len(alerts) == 0, "Should default to no alerts if data missing (safer)"
