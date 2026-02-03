
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Optional imports for new dependencies
try:
    from pykalman import KalmanFilter
except ImportError:
    KalmanFilter = None

try:
    import markovify
except ImportError:
    markovify = None

logger = logging.getLogger(__name__)

class SignalService:
    def __init__(self):
        if not KalmanFilter:
            logger.warning("pykalman not installed. Kalman features will be limited.")
        if not markovify:
            logger.warning("markovify not installed. Markov features will be limited.")

    def get_kalman_signal(self, ticker_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply Kalman Filter to smooth price data and generate trend signals.
        Returns latest signal and current values.
        """
        if not KalmanFilter:
            return {"error": "KalmanFilter library missing"}
        
        if ticker_data.empty or 'Close' not in ticker_data.columns:
            return {"error": "Invalid data"}

        try:
            prices = ticker_data['Close']
            
            # Simple 1D Kalman Filter
            kf = KalmanFilter(transition_matrices=[1],
                              observation_matrices=[1],
                              initial_state_mean=prices.iloc[0],
                              initial_state_covariance=1,
                              observation_covariance=1,
                              transition_covariance=0.01)
            
            state_means, _ = kf.filter(prices.values)
            
            current_price = float(prices.iloc[-1])
            kalman_mean = float(state_means[-1])
            
            # Signal Logic
            # If Price > Kalman Mean: Bullish / Overbought (depending on context, simplified here as "Above Trend")
            # If Price < Kalman Mean: Bearish / Oversold
            
            signal = "Above Trend (Bullish/Overbought)" if current_price > kalman_mean else "Below Trend (Bearish/Oversold)"
            
            return {
                "signal": signal,
                "current_price": current_price,
                "kalman_mean": kalman_mean,
                "timestamp": str(ticker_data.index[-1])
            }
        except Exception as e:
            logger.error(f"Error in Kalman Filter: {e}", exc_info=True)
            return {"error": str(e)}

    def get_markov_probabilities(self, ticker_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate transition probabilities based on historical returns.
        """
        if not markovify:
            return {"error": "markovify library missing"}

        if ticker_data.empty:
            return {"error": "No data"}

        try:
            # internal helper to discretize returns
            # Using 'Close'
            df = ticker_data.copy()
            df['Return'] = df['Close'].pct_change()
            
            def get_state(ret):
                if pd.isna(ret): return "Skip"
                if ret > 0.01: return "UP_BIG"
                if ret > 0: return "UP_SMALL"
                if ret == 0: return "FLAT"
                if ret > -0.01: return "DOWN_SMALL"
                return "DOWN_BIG"

            df['State'] = df['Return'].apply(get_state)
            states = df['State'][df['State'] != "Skip"].tolist()
            
            if not states:
                return {"error": "Not enough data for states"}

            # Build corpus
            text_corpus = " ".join(states)
            
            # Build model
            text_model = markovify.Text(text_corpus, state_size=1)
            
            # Get current state
            current_state = states[-1]
            
            # Calculate next state probabilities (Manual inspection of the model or simulation)
            # Markovify is generative, getting raw probabilities isn't its primary API.
            # We can simulate N trials to get probabilities, or assume the chain dict is accessible.
            # For robustness/simplicity, let's verify empirically from the data for the 'transitions' dict
            
            # Get transitions from the actual list for the current state
            transitions = {}
            total = 0
            
            # Simple frequentist approach for the current state transitions
            # Find all indices where state == current_state
            indices = [i for i, x in enumerate(states[:-1]) if x == current_state]
            
            if indices:
                next_states = [states[i+1] for i in indices]
                counts = pd.Series(next_states).value_counts()
                transitions = (counts / len(next_states)).to_dict()
            
            return {
                "current_state": current_state,
                "transitions": transitions
            }
            
        except Exception as e:
            logger.error(f"Error in Markov Chain: {e}", exc_info=True)
            return {"error": str(e)}

    def get_roll_vs_hold_advice(self, ticker: str, option_details: Dict, mock_price_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Compare Expected Value of Holding vs Rolling based on Markov simulations.
        """
        try:
            # 1. Get Data
            if mock_price_data is not None:
                data = mock_price_data
            else:
                import yfinance as yf
                data = yf.download(ticker, period="1y", interval="1d", progress=False)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
            
            # 2. Get Markov Probabilities
            markov_result = self.get_markov_probabilities(data)
            
            if "error" in markov_result:
                return {"recommendation": "UNKNOWN", "reason": markov_result["error"]}
                
            transitions = markov_result.get("transitions", {})
            current_state = markov_result.get("current_state", "UNKNOWN")
            
            # 3. Simple Heuristic for now (MVP)
            # If probability of UP > 50% and we have a Call -> HOLD ?? 
            # Needs Context: Is it a Covered Call (Short) or Long Call?
            # Assuming typical "Juicy Fruit" context: Short Covered Calls.
            # If stock goes UP_BIG, Short Call loses money (or gets exercised).
            # If stock goes DOWN, Short Call makes money.
            
            # Calculate Prob(UP) vs Prob(DOWN)
            prob_up = transitions.get("UP_BIG", 0) + transitions.get("UP_SMALL", 0)
            prob_down = transitions.get("DOWN_BIG", 0) + transitions.get("DOWN_SMALL", 0)
            
            # Scoring
            # Roll Score: High if UP probability is high (Threat to Short Call) -> Rolling up/out might be defensive
            # Hold Score: High if DOWN probability is high (Profit for Short Call)
            
            roll_score = prob_up * 100
            hold_score = prob_down * 100
            
            # Calculate Confidence (Difference in scores, normalized 0-100)
            # Max possible difference is 100 (100 vs 0)
            confidence = abs(roll_score - hold_score)
            
            recommendation = "HOLD"
            reason = f"Market showing weakness (Prob Down: {prob_down:.0%}). Good for Short Calls."
            
            if roll_score > hold_score:
                if roll_score > 60:
                     recommendation = "ROLL"
                     reason = f"High probability of upwards move ({prob_up:.0%}). Consider rolling to avoid assignment/capture gain."
                else:
                     recommendation = "CAUTION"
                     reason = f"Slight bias upwards ({prob_up:.0%}). Monitor closely."
            
            return {
                "recommendation": recommendation,
                "reason": reason,
                "confidence": round(confidence, 1),
                "hold_score": round(hold_score, 1),
                "roll_score": round(roll_score, 1),
                "prob_up": round(prob_up, 2),
                "prob_down": round(prob_down, 2),
                "current_state": current_state
            }
            
        except Exception as e:
            return {"recommendation": "ERROR", "reason": str(e)}
