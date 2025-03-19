import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np
import time
import sys

def get_current_price(ticker):
    """Get current stock price with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            # Try different price attributes as fallbacks
            price = stock.info.get('regularMarketPrice') or \
                   stock.info.get('currentPrice') or \
                   stock.info.get('previousClose')
            if price:
                return price
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1} of {max_retries} for price fetch...")
                time.sleep(2)  # Wait before retry
            else:
                raise Exception(f"Could not fetch price after {max_retries} attempts: {str(e)}")
    return None

def analyze_option_chain(ticker_symbol, min_volume=100, max_expirations=3):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for out-of-the-money call options.
    """
    print(f"\nFetching data for {ticker_symbol}...")
    
    try:
        # Get current stock price
        current_price = get_current_price(ticker_symbol)
        if not current_price:
            print(f"Error: Could not fetch current price for {ticker_symbol}")
            return
        
        print(f"Current Price: ${current_price:.2f}")
        
        # Get stock object
        stock = yf.Ticker(ticker_symbol)
        
        # Get expiration dates
        try:
            all_expirations = stock.options
            if not all_expirations:
                print("No options data available")
                return
                
            expirations = all_expirations[:max_expirations]
            print(f"Found {len(all_expirations)} expiration dates, analyzing first {len(expirations)}")
        except Exception as e:
            print(f"Error fetching option dates: {str(e)}")
            return
        
        results = []
        
        # Analyze each expiration date
        for expiry in expirations:
            print(f"\nAnalyzing options for expiration {expiry}...")
            try:
                # Get option chain
                opt = stock.option_chain(expiry)
                if not opt or not hasattr(opt, 'calls'):
                    print(f"No call options data for {expiry}")
                    continue
                
                calls = opt.calls
                
                # Filter for out-of-the-money calls
                otm_calls = calls[calls['strike'] > current_price]
                
                # Filter for minimum volume
                otm_calls = otm_calls[otm_calls['volume'] >= min_volume]
                
                if len(otm_calls) == 0:
                    print(f"No suitable OTM calls found for {expiry}")
                    continue
                
                print(f"Found {len(otm_calls)} suitable OTM calls")
                
                # Calculate metrics for each option
                for _, option in otm_calls.iterrows():
                    days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
                    
                    if days_to_expiry <= 0:
                        continue
                    
                    time_value = option['lastPrice']  # For OTM calls, entire premium is time value
                    time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
                    
                    results.append({
                        'Expiration': expiry,
                        'Strike': option['strike'],
                        'Last Price': option['lastPrice'],
                        'Bid': option.get('bid', 0),
                        'Ask': option.get('ask', 0),
                        'Volume': option['volume'],
                        'Open Interest': option['openInterest'],
                        'Time Value': time_value,
                        'Days to Expiry': days_to_expiry,
                        'Ann. Time Value %': time_value_pct,
                        'Distance OTM %': ((option['strike'] - current_price) / current_price) * 100
                    })
                    
            except Exception as e:
                print(f"Error processing {expiry}: {str(e)}")
                continue
        
        if not results:
            print("\nNo suitable options found matching criteria")
            return
        
        # Convert results to DataFrame and sort
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Ann. Time Value %', ascending=False)
        
        # Print results
        print("\nTop 10 Time Value Opportunities for OTM Calls:")
        print("=============================================")
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_results.head(10).to_string(index=False))
        
        return df_results
        
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return None

def main():
    print("Options Chain Analyzer for Time Value Opportunities")
    print("================================================")
    
    while True:
        ticker = input("\nEnter stock ticker symbol (or 'quit' to exit): ").upper()
        if ticker.lower() == 'quit':
            break
            
        try:
            min_vol = int(input("Enter minimum option volume (default 100): ") or "100")
            max_exp = int(input("Enter maximum number of expiration dates to analyze (default 3): ") or "3")
            
            analyze_option_chain(ticker, min_vol, max_exp)
            
        except ValueError as e:
            print("Invalid input. Please enter numeric values for volume and expiration count.")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    main()