import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np
import time

def get_current_price(ticker):
    """Get current stock price with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            price = stock.history(period='1d')['Close'].iloc[-1]
            if price:
                return price
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1} of {max_retries} for price fetch...")
                time.sleep(1)
            else:
                raise Exception(f"Could not fetch price after {max_retries} attempts: {str(e)}")
    return None

def analyze_option_chain(ticker_symbol="ORCL", min_volume=100, max_expirations=2, min_annual_tv_pct=9.9, max_otm_pct=5.0):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for near-the-money call options.
    
    Args:
        ticker_symbol (str): Stock symbol
        min_volume (int): Minimum option volume
        max_expirations (int): Number of expiration dates to analyze
        min_annual_tv_pct (float): Minimum annualized time value percentage
        max_otm_pct (float): Maximum percentage out-of-the-money to consider
    """
    print(f"\nFetching data for {ticker_symbol}...")
    
    try:
        # Get current stock price using simplified method
        current_price = get_current_price(ticker_symbol)
        if not current_price:
            print(f"Error: Could not fetch current price for {ticker_symbol}")
            return
        
        print(f"Current Price: ${current_price:.2f}")
        
        # Get stock object
        stock = yf.Ticker(ticker_symbol)
        
        # Get expiration dates
        all_expirations = stock.options
        if not all_expirations:
            print("No options data available")
            return
            
        expirations = all_expirations[:max_expirations]
        print(f"Analyzing {len(expirations)} expiration dates")
        
        results = []
        
        # Analyze each expiration date
        for expiry in expirations:
            print(f"Processing {expiry}...")
            
            # Get option chain
            opt = stock.option_chain(expiry)
            calls = opt.calls
            
            # Filter for out-of-the-money calls
            otm_calls = calls[calls['strike'] > current_price]
            otm_calls = otm_calls[otm_calls['volume'] >= min_volume]
            
            if len(otm_calls) == 0:
                continue
            
            # Calculate metrics for each option
            for _, option in otm_calls.iterrows():
                days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
                
                if days_to_expiry <= 0:
                    continue
                
                time_value = option['lastPrice']
                time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
                
                results.append({
                    'Expiration': expiry,
                    'Strike': option['strike'],
                    'Last': option['lastPrice'],
                    'Bid': option['bid'],
                    'Ask': option['ask'],
                    'Volume': option['volume'],
                    'OI': option['openInterest'],
                    'Time Val': time_value,
                    'Days': days_to_expiry,
                    'Ann.TV%': time_value_pct,
                    'OTM%': ((option['strike'] - current_price) / current_price) * 100
                })
        
        if not results:
            print("\nNo suitable options found matching criteria")
            return
        
        # Convert results to DataFrame and sort
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Ann.TV%', ascending=False)
        
        # Print results
        print("\nTop 10 Time Value Opportunities for OTM Calls:")
        print("=============================================")
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        print(df_results.head(10))
        
        return df_results
        
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return None

if __name__ == "__main__":
    analyze_option_chain("ORCL", min_volume=50, max_expirations=2)