import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

def analyze_option_chain(ticker_symbol, min_volume=100):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for out-of-the-money call options.
    
    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'ORCL')
        min_volume (int): Minimum option volume to consider
    """
    # Get stock information
    stock = yf.Ticker(ticker_symbol)
    current_price = stock.info['regularMarketPrice']
    print(f"\nAnalyzing {ticker_symbol} - Current Price: ${current_price:.2f}\n")
    
    # Get all available expiration dates
    try:
        expirations = stock.options
    except:
        print("Error: Could not fetch option chain data")
        return
    
    # Store results
    results = []
    
    # Analyze each expiration date
    for expiry in expirations:
        # Get call options for this expiration
        opt = stock.option_chain(expiry)
        calls = opt.calls
        
        # Filter for out-of-the-money calls
        otm_calls = calls[calls['strike'] > current_price]
        
        # Filter for minimum volume
        otm_calls = otm_calls[otm_calls['volume'] >= min_volume]
        
        if len(otm_calls) == 0:
            continue
            
        # Calculate time value
        # Time value = Option price - (Current stock price - Strike price)
        for _, option in otm_calls.iterrows():
            time_value = option['lastPrice']  # For OTM calls, entire premium is time value
            days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
            
            # Calculate annualized time value percentage
            time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
            
            results.append({
                'Expiration': expiry,
                'Strike': option['strike'],
                'Last Price': option['lastPrice'],
                'Volume': option['volume'],
                'Open Interest': option['openInterest'],
                'Time Value': time_value,
                'Days to Expiry': days_to_expiry,
                'Ann. Time Value %': time_value_pct
            })
    
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
    print(df_results.head(10).to_string(index=False))

def main():
    ticker = input("Enter stock ticker symbol (e.g., ORCL): ").upper()
    min_vol = int(input("Enter minimum option volume (default 100): ") or "100")
    
    analyze_option_chain(ticker, min_vol)

if __name__ == "__main__":
    main()