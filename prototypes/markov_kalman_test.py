
import yfinance as yf
import numpy as np
import pandas as pd
# Try/Except for imports to allow script to run even if tools aren't fully installed in env yet (concept check)
try:
    from pykalman import KalmanFilter
    import markovify
except ImportError as e:
    print(f"Missing dependency: {e}")
    # Mocking for logic verification if libs missing in this context
    KalmanFilter = None
    markovify = None

def test_kalman_smoothing(ticker="SPY"):
    if not KalmanFilter:
        print("Skipping Kalman test due to missing library.")
        return pd.DataFrame()

    print(f"Fetching data for {ticker}...")
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty:
            print("No data fetched.")
            return pd.DataFrame()
            
        # yfinance can return multi-index columns, fix that if needed
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        prices = data['Close']

        # Kalman Filter for smoothing (Mean Reversion / Trend)
        # Simple 1D Kalman Filter
        kf = KalmanFilter(transition_matrices=[1],
                          observation_matrices=[1],
                          initial_state_mean=prices.iloc[0],
                          initial_state_covariance=1,
                          observation_covariance=1,
                          transition_covariance=0.01)
        
        state_means, _ = kf.filter(prices.values)
        
        data['Kalman_Mean'] = state_means
        
        # Simple strategy: Price vs Kalman Mean
        # If Price < Kalman Mean, potentially Oversold (Mean Reversion Buy)
        # If Price > Kalman Mean, potentially Overbought
        data['Signal'] = np.where(prices > data['Kalman_Mean'], 'Above Trend (Bullish/Overbought)', 'Below Trend (Bearish/Oversold)')
        
        print("\n--- Kalman Filter Results (Tail) ---")
        print(data[['Close', 'Kalman_Mean', 'Signal']].tail())
        return data
    except Exception as e:
        print(f"Error in Kalman test: {e}")
        return pd.DataFrame()

def test_markov_chain(data):
    if not markovify or data.empty:
        print("Skipping Markov test.")
        return

    # Create states from daily returns
    # Using 'Close'
    data['Return'] = data['Close'].pct_change()
    
    # Discretize returns into states
    # State definitions:
    # UP_BIG: > 1%
    # UP_SMALL: 0% to 1%
    # FLAT: 0%
    # DOWN_SMALL: -1% to 0%
    # DOWN_BIG: < -1%
    
    def get_state(ret):
        if pd.isna(ret): return "Skip"
        if ret > 0.01: return "UP_BIG"
        if ret > 0: return "UP_SMALL"
        if ret == 0: return "FLAT"
        if ret > -0.01: return "DOWN_SMALL"
        return "DOWN_BIG"

    data['State'] = data['Return'].apply(get_state)
    states = data['State'][data['State'] != "Skip"].tolist()
    
    # Markovify works on text, so join states into a "sentence"
    text_corpus = " ".join(states)
    
    # Build model (state_size=1 means it looks at current state to predict next)
    # state_size=2 would look at previous 2 states
    text_model = markovify.Text(text_corpus, state_size=1) 
    
    print("\n--- Markov Chain Transition Probabilities (Derived/Simulated) ---")
    # Generate some sequences
    for i in range(3):
        # We can try to use make_sentence to see generated paths
        sent = text_model.make_sentence()
        if sent:
            print(f"Simulated Path {i+1}: {sent}")
    
    # Manual Transition Matrix for verification
    print("\n--- Manual Transition Matrix (Empirical) ---")
    df_trans = pd.DataFrame({'Current': states[:-1], 'Next': states[1:]})
    ct = pd.crosstab(df_trans['Current'], df_trans['Next'], normalize='index')
    print(ct)

if __name__ == "__main__":
    print("Starting Prototype...")
    try:
        data = test_kalman_smoothing()
        test_markov_chain(data)
    except Exception as e:
        print(f"Global Error: {e}")
