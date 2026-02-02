import pytest
import pandas as pd
import numpy as np
from app.utils.greeks_calculator import GreeksCalculator

def test_calculate_call_greeks_atm():
    """Test Greeks for At-The-Money Call."""
    # S=100, K=100, t=1yr, r=5%, sigma=20%
    # Expected: Delta ~0.5 (+ drift) -> ~0.6 with BS? No, ATM Delta roughly 0.5 for small r/sigma.
    # Black Scholes ATM Delta is N(d1).  
    
    data = {
        'strike': [100.0],
        'time_to_expiry_years': [1.0],
        'impliedVolatility': [0.2],
        'type': ['c']
    }
    df = pd.DataFrame(data)
    
    result = GreeksCalculator.calculate_dataframe(df, underlying_price=100.0, risk_free_rate=0.05)
    
    delta = result.iloc[0]['delta']
    gamma = result.iloc[0]['gamma']
    
    # Delta should be around 0.5 to 0.6
    assert 0.5 < delta < 0.7 
    assert gamma > 0
    assert 'theta' in result.columns

def test_calculate_put_greeks_itm():
    """Test Greeks for In-The-Money Put."""
    # S=100, K=120 (Deep ITM Put)
    # Expected: Delta ~ -1.0
    
    data = {
        'strike': [120.0],
        'time_to_expiry_years': [0.1],
        'impliedVolatility': [0.2],
        'type': ['p']
    }
    df = pd.DataFrame(data)
    
    result = GreeksCalculator.calculate_dataframe(df, underlying_price=100.0, risk_free_rate=0.05)
    
    delta = result.iloc[0]['delta']
    # ITM Put Delta is close to -1
    assert -1.0 <= delta < -0.8

def test_missing_columns():
    """Test handling of invalid DF."""
    df = pd.DataFrame({'wrong': [1, 2, 3]})
    result = GreeksCalculator.calculate_dataframe(df, 100)
    # Should satisfy "Return unmodified"
    assert 'delta' not in result.columns

def test_zero_volatility():
    """Test robustness against bad data (Zero IV)."""
    data = {
        'strike': [100.0],
        'time_to_expiry_years': [1.0],
        'impliedVolatility': [0.0], # Zero Vol
        'type': ['c']
    }
    df = pd.DataFrame(data)
    
    # Should not crash
    result = GreeksCalculator.calculate_dataframe(df, underlying_price=100.0)
    
    # Intrinsic value logic applies, or it returns specific greeks.
    # py_vollib might return exact boundaries.
    assert 'delta' in result.columns
