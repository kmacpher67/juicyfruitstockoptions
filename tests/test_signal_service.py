
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from app.services.signal_service import SignalService

# Mock data fixtures
@pytest.fixture
def mock_price_data():
    dates = pd.date_range(start="2024-01-01", periods=100)
    # Create a trend + noise
    prices = np.linspace(100, 110, 100) + np.random.normal(0, 1, 100)
    df = pd.DataFrame({'Close': prices}, index=dates)
    return df

@pytest.fixture
def mock_option_chain():
    return {
        "calls": pd.DataFrame({
            "strike": [100, 105, 110],
            "lastPrice": [10.5, 6.2, 2.1],
            "impliedVolatility": [0.2, 0.2, 0.2]
        })
    }

class TestSignalService:
    
    def test_initialization(self):
        service = SignalService()
        assert service is not None

    @patch('app.services.signal_service.KalmanFilter')
    def test_get_kalman_signal_bullish(self, mock_kf_cls, mock_price_data):
        # Setup mock Kalman Filter to return values lower than current price (Bullish)
        mock_kf_instance = mock_kf_cls.return_value
        # Mocking filter() to return (state_means, state_covariances)
        # Create a mean line strictly below the price
        mock_means = mock_price_data['Close'].values - 5 
        mock_kf_instance.filter.return_value = (mock_means, None)

        service = SignalService()
        result = service.get_kalman_signal(mock_price_data)
        
        assert result['signal'] == 'Above Trend (Bullish/Overbought)'
        assert result['current_price'] > result['kalman_mean']

    @patch('app.services.signal_service.KalmanFilter')
    def test_get_kalman_signal_bearish(self, mock_kf_cls, mock_price_data):
        # Setup mock Kalman Filter to return values higher than current price (Bearish)
        mock_kf_instance = mock_kf_cls.return_value
        mock_means = mock_price_data['Close'].values + 5
        mock_kf_instance.filter.return_value = (mock_means, None)

        service = SignalService()
        result = service.get_kalman_signal(mock_price_data)

        assert result['signal'] == 'Below Trend (Bearish/Oversold)'

    def test_get_markov_probabilities(self, mock_price_data):
        # This test relies on the actual markovify lib logic or a simple mock if we wanted
        # But let's test the data transformation logic primarily
        service = SignalService()
        
        # We need enough data to generate states
        result = service.get_markov_probabilities(mock_price_data)
        
        assert 'transitions' in result
        assert 'current_state' in result
        # Check if transitions is a dict of probabilities
        assert isinstance(result['transitions'], dict)

    def test_get_roll_vs_hold_advice(self):
        service = SignalService()
        ticker = "SPY"
        option_details = {"expiration": "2024-02-01", "strike": 500}
        
        # Mock internal methods to isolate advice logic
        service.get_markov_probabilities = MagicMock(return_value={
            'transitions': {'UP_SMALL': 0.6, 'DOWN_SMALL': 0.4},
            'current_state': 'UP_SMALL'
        })
        
        advice = service.get_roll_vs_hold_advice(ticker, option_details, mock_price_data=pd.DataFrame({'Close': [100]}))
        
        assert 'recommendation' in advice
        assert 'hold_score' in advice
        assert 'roll_score' in advice
