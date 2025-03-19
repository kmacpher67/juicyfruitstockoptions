import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np
from datetime import timedelta

def analyze_option_chain(ticker_symbol, min_volume=100, max_expirations=3):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for out-of-the-money call options.
    
    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'ORCL')
        min_volume (int): Minimum option volume to consider
        max_expirations (int): Maximum number of expiration dates to analyze
    """
    # Get stock information
    stock = yf.Ticker(ticker_symbol)
    
    try:
        current_price = stock.info['regularMarketPrice']
        print(f"\nAnalyzing {ticker_symbol} - Current Price: ${current_price:.2f}\n")
    except:
        print(f"Error: Could not fetch current price for {ticker_symbol}")
        return
    
    # Get near-term expiration dates
    try:
        all_expirations = stock.options
        expirations = all_expirations[:max_expirations]  # Analyze only next few expiration dates
        print(f"Analyzing {len(expirations)} expiration dates of {len(all_expirations)} available\n")
    except:
        print("Error: Could not fetch option chain data")
        return
    
    results = []
    
    # Analyze each expiration date
    for expiry in expirations:
        try:
            opt = stock.option_chain(expiry)
            calls = opt.calls
            
            # Filter for out-of-the-money calls
            otm_calls = calls[calls['strike'] > current_price]
            
            # Filter for minimum volume
            otm_calls = otm_calls[otm_calls['volume'] >= min_volume]
            
            if len(otm_calls) == 0:
                continue
                
            # Calculate time value for each option
            for _, option in otm_calls.iterrows():
                days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
                
                # Skip if already expired
                if days_to_expiry <= 0:
                    continue
                
                # For OTM calls, the entire premium is time value
                time_value = option['lastPrice']
                
                # Calculate time value percentage (annualized)
                time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
                
                results.append({
                    'Expiration': expiry,
                    'Strike': option['strike'],
                    'Last Price': option['lastPrice'],
                    'Volume': option['volume'],
                    'Open Interest': option['openInterest'],
                    'Time Value': time_value,
                    'Days to Expiry': days_to_expiry,
                    'Ann. Time Value %': time_value_pct,
                    'Distance OTM %': ((option['strike'] - current_price) / current_price) * 100
                })
        
        except Exception as e:
            print(f"Error processing expiration {expiry}: {str(e)}")
            continue
    
    if not results:
        print("No suitable options found matching criteria")
        return
        
    # Convert results to DataFrame and sort by annualized time value
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Ann. Time Value %', ascending=False)
    
    # Print top 10 opportunities
    print("\nTop 10 Time Value Opportunities for OTM Calls:")
    print("=============================================")
    pd.set_option('display.float_format', lambda x: '%.2f' % x)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(df_results.head(10).to_string(index=False))

if __name__ == "__main__":
    ticker = input("Enter stock ticker symbol (e.g., ORCL): ").upper()
    min_vol = int(input("Enter minimum option volume (default 100): ") or "100")
    
    analyze_option_chain(ticker, min_vol)