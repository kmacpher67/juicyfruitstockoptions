import pandas as pd
import numpy as np
import logging
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

class GreeksCalculator:
    """
    Utility to calculate Option Greeks (Delta, Gamma, Theta) using Black-Scholes model.
    """
    
    @staticmethod
    def calculate_dataframe(df: pd.DataFrame, underlying_price: float, risk_free_rate: float = 0.045) -> pd.DataFrame:
        """
        Enriches a yfinance option chain DataFrame with Greeks.
        
        Args:
            df (pd.DataFrame): Must contain columns: 'strike', 'time_to_expiry_years', 'impliedVolatility', 'type' ('c' or 'p').
            underlying_price (float): Current price of the underlying asset.
            risk_free_rate (float): Annualized risk-free rate (default 4.5%).
            
        Returns:
            pd.DataFrame: Original DataFrame with added 'delta', 'gamma', 'theta' columns.
        """
        if df.empty:
            logging.warning("GreeksCalculator received empty DataFrame.")
            return df

        required_cols = {'strike', 'time_to_expiry_years', 'impliedVolatility', 'type'}
        if not required_cols.issubset(df.columns):
            logging.error(f"DataFrame missing required columns for Greeks calculation: {required_cols - set(df.columns)}")
            return df # Return unmodified

        try:
            # Prepare inputs
            # Map 'type' column to 'c' or 'p' if needed (yfinance usually provides 'call'/'put' objects, 
            # but if we passed a constructed DF, ensure strict 'c'/'p')
            # Assuming 'type' column has 'c' or 'p'.
            
            # vectorized_implied_volatility isn't needed if we trust yfinance's 'impliedVolatility'.
            # We go straight to get_all_greeks.
            
            # Handle potential NaNs in IV or Time
            df = df.copy()
            df['impliedVolatility'] = df['impliedVolatility'].fillna(0)
            df['time_to_expiry_years'] = df['time_to_expiry_years'].fillna(0)
            
            # Avoid Zero Division or errors with 0 time?
            # py_vollib handles 0 time by returning intrinsic value / appropriate greeks (Delta 0 or 1).
            
            greeks = get_all_greeks(
                flag=df['type'], # 'c' or 'p'
                S=underlying_price,
                K=df['strike'],
                t=df['time_to_expiry_years'],
                r=risk_free_rate,
                sigma=df['impliedVolatility'],
                q=0, # Dividend yield - ignored for now as defined in plan
                model='black_scholes_merton',
                return_as='dict'
            )
            
            df['delta'] = greeks['delta']
            df['gamma'] = greeks['gamma']
            df['theta'] = greeks['theta'] # Annualized Theta
            
            return df
            
        except Exception as e:
            logging.error(f"Failed to calculate Greeks: {e}")
            # Ensure columns exist even on failure to avoid downstream key errors
            df['delta'] = 0.0
            df['gamma'] = 0.0
            df['theta'] = 0.0
            return df
