import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from app.services.roll_service import RollService

# Removed unused fixture mock_yf_ticker

@patch("app.services.roll_service.GreeksCalculator")
@patch("app.services.opportunity_service.MongoClient")
@patch("app.services.roll_service.SignalService")
@patch("app.services.roll_service.OpportunityService")
@patch("yfinance.Ticker")
def test_find_rolls_calls(mock_yf_ticker_cls, mock_opp_service, mock_signal_service, mock_mongo, mock_greeks_calc):
    # Setup Data
    mock_yf_ticker = MagicMock()
    mock_yf_ticker_cls.return_value = mock_yf_ticker

    # Configure Greeks Calculator
    def mock_calc_greeks(df, price=None):
        df['delta'] = 0.5
        df['gamma'] = 0.05
        df['theta'] = -0.05
        return df
    mock_greeks_calc.calculate_dataframe.side_effect = mock_calc_greeks
    
    # Configure fast_info as a dict-like object (MagicMock matches dict access usually, but let's be safe)
    # yfinance.Ticker.fast_info is accessed via keys.
    mock_yf_ticker.fast_info = {'last_price': 100.0, 'previous_close': 99.0}
    
    # Mock info to avoid implicit MagicMock causing TypeError in date parsing
    mock_yf_ticker.info = {"exDividendDate": None}

    mock_yf_ticker.options = ("2025-01-17", "2025-02-21")

    # Old Chain for 2025-01-17
    old_df = pd.DataFrame([
        {'strike': 100.0, 'ask': 5.0, 'bid': 4.8, 'lastPrice': 4.9}
    ])
    # Use SimpleNamespace to avoid MagicMock attribute conflicts with 'calls'
    mock_old_chain = SimpleNamespace(calls=old_df, puts=pd.DataFrame())

    # New Chain for 2025-02-21
    new_df = pd.DataFrame([
        # Strike 100 (Calendar Roll)
        {'strike': 100.0, 'ask': 7.0, 'bid': 6.8, 'lastPrice': 6.9, 'impliedVolatility': 0.2, 'time_to_expiry_years': 0.1},
        # Strike 105 (Up and Out)
        {'strike': 105.0, 'ask': 4.0, 'bid': 3.8, 'lastPrice': 3.9, 'impliedVolatility': 0.2, 'time_to_expiry_years': 0.1}
    ])
    mock_new_chain = SimpleNamespace(calls=new_df, puts=pd.DataFrame())

    # Mock option_chain calls
    def get_chain(date):
        if date == "2025-01-17": return mock_old_chain
        if date == "2025-02-21": return mock_new_chain
        return SimpleNamespace(calls=pd.DataFrame(), puts=pd.DataFrame())

    mock_yf_ticker.option_chain.side_effect = get_chain
    

    # Configure Signal Service to avoid TypeErrors
    # IMPORTANT: mock_signal_service is the CLASS mock. Its return_value is the INSTANCE.
    mock_signal_instance = mock_signal_service.return_value
    mock_signal_instance.get_roll_vs_hold_advice.return_value = {
        "prob_up": 0.5,
        "prob_down": 0.5,
        "recommendation": "HOLD"
    }
    
    # Act
    service = RollService()
    result = service.find_rolls("AAPL", 100.0, "2025-01-17", "call")
    
    # Assert
    assert "error" not in result
    rolls = result["rolls"]
    assert len(rolls) == 1
    
    # Check Calendar Roll (Same Strike)
    # Sell Bid 6.8 - Buy Ask 5.0 = 1.8 Credit
    cal_roll = next(r for r in rolls if r["strike"] == 100.0)
    assert cal_roll["net_credit"] == 1.8
    assert cal_roll["roll_type"] == "Roll Out"
    assert "delta" in cal_roll
    assert "gamma" in cal_roll
    assert "theta" in cal_roll
    
    # Check Up and Out Roll (Strike 105)
    # Sell Bid 3.8 - Buy Ask 5.0 = -1.2 Debit
    # -1.2 < -0.10, so it might be filtered out? 
    # Logic in service: if net_credit > -0.10.
    # So this one should NOT be in the list?
    
    roll_105 = next((r for r in rolls if r["strike"] == 105.0), None)
    # Assert it is missing because -1.2 is a big cost
    assert roll_105 is None
