import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from app.services.roll_service import RollService

@pytest.fixture
def mock_yf_ticker():
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_ticker_cls.return_value = mock_instance
        yield mock_instance

def test_find_rolls_calls(mock_yf_ticker):
    # Setup Data
    mock_yf_ticker.fast_info = {'last_price': 100.0}
    # Dates: Today is 2025-01-01. Old Exp 2025-01-17. New Exp 2025-02-21
    mock_yf_ticker.options = ("2025-01-17", "2025-02-21")
    
    # Old Chain for 2025-01-17
    old_df = pd.DataFrame([
        {'strike': 100.0, 'ask': 5.0, 'bid': 4.8, 'lastPrice': 4.9}
    ])
    mock_old_chain = MagicMock()
    mock_old_chain.calls = old_df
    
    # New Chain for 2025-02-21
    new_df = pd.DataFrame([
        # Strike 100 (Calendar Roll)
        {'strike': 100.0, 'ask': 7.0, 'bid': 6.8, 'lastPrice': 6.9},
        # Strike 105 (Up and Out)
        {'strike': 105.0, 'ask': 4.0, 'bid': 3.8, 'lastPrice': 3.9}
    ])
    mock_new_chain = MagicMock()
    mock_new_chain.calls = new_df
    
    # Mock option_chain calls
    def get_chain(date):
        if date == "2025-01-17": return mock_old_chain
        if date == "2025-02-21": return mock_new_chain
        return MagicMock()
        
    mock_yf_ticker.option_chain.side_effect = get_chain
    
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
    
    # Check Up and Out Roll (Strike 105)
    # Sell Bid 3.8 - Buy Ask 5.0 = -1.2 Debit
    # -1.2 < -0.10, so it might be filtered out? 
    # Logic in service: if net_credit > -0.10.
    # So this one should NOT be in the list?
    # Wait, -1.2 is NOT > -0.10. It is smaller.
    # Ah, the logic `if net_credit > -0.10` filters out large debits.
    # So 105 strike should be missing.
    
    roll_105 = next((r for r in rolls if r["strike"] == 105.0), None)
    # Assert it is missing because -1.2 is a big cost
    assert roll_105 is None

