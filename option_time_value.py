import yfinance as yf
import pandas as pd
from datetime import datetime
import time

def get_option_chain(ticker):
    """
    Get option chain for a ticker with rate limit handling
    """
    try:
        stock = yf.Ticker(ticker)
        time.sleep(1)  # Rate limit handling
        
        # Get current stock price
        current_price = stock.info['regularMarketPrice']
        
        # Get all expiration dates
        dates = stock.options
        
        if not dates:
            return None, None, None
            
        # We'll look at the first 3 expiration dates to limit API calls
        dates = dates[:3]
        
        all_calls = []
        for date in dates:
            try:
                opt = stock.option_chain(date)
                calls = opt.calls
                calls['expirationDate'] = date
                calls['stockPrice'] = current_price
                all_calls.append(calls)
                time.sleep(1)  # Rate limit handling
            except Exception as e:
                print(f"Error getting option chain for {ticker} date {date}: {e}")
                continue
                
        if not all_calls:
            return None, None, None
            
        return pd.concat(all_calls), current_price, ticker
    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None, None, None

def calculate_time_value(row):
    """
    Calculate time value for an option
    Time Value = Option Price - (Stock Price - Strike Price)
    """
    intrinsic_value = max(0, row['stockPrice'] - row['strike'])
    time_value = row['lastPrice'] - intrinsic_value
    return time_value

def analyze_options(tickers=["ORCL", "AMZN", "XOM"], min_time_value=0.10):
    """
    Analyze options for multiple tickers and find best time value opportunities
    """
    all_opportunities = []
    
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...")
        option_chain, current_price, ticker_name = get_option_chain(ticker)
        
        if option_chain is None:
            continue
            
        # Filter for OTM calls
        otm_calls = option_chain[option_chain['strike'] > current_price].copy()
        
        if len(otm_calls) == 0:
            continue
            
        # Calculate time value
        otm_calls['timeValue'] = otm_calls.apply(calculate_time_value, axis=1)
        
        # Filter by minimum time value
        good_opportunities = otm_calls[otm_calls['timeValue'] >= min_time_value].copy()
        
        if len(good_opportunities) > 0:
            good_opportunities['ticker'] = ticker_name
            good_opportunities['percentOTM'] = ((good_opportunities['strike'] - current_price) / current_price) * 100
            all_opportunities.append(good_opportunities)
    
    if not all_opportunities:
        print("No opportunities found matching criteria")
        return None
        
    # Combine all opportunities
    all_df = pd.concat(all_opportunities)
    
    # Select and rename relevant columns
    result = all_df[[
        'ticker', 'expirationDate', 'strike', 'lastPrice', 'timeValue', 
        'percentOTM', 'volume', 'openInterest'
    ]].copy()
    
    # Sort by time value descending
    result = result.sort_values('timeValue', ascending=False)
    
    # Format the results
    result['percentOTM'] = result['percentOTM'].round(2)
    result['timeValue'] = result['timeValue'].round(2)
    result['strike'] = result['strike'].round(2)
    result['lastPrice'] = result['lastPrice'].round(2)
    
    return result

def main():
    # Get user input for tickers
    default_tickers = ["ORCL", "AMZN", "XOM"]
    user_input = input(f"Enter stock tickers separated by comma (default: {','.join(default_tickers)}): ").strip()
    
    if user_input:
        tickers = [ticker.strip().upper() for ticker in user_input.split(',')]
    else:
        tickers = default_tickers
    
    # Get minimum time value
    while True:
        try:
            min_time_value = float(input("Enter minimum time value (default: 0.10): ") or 0.10)
            break
        except ValueError:
            print("Please enter a valid number")
    
    print("\nAnalyzing options... This may take a moment.")
    results = analyze_options(tickers, min_time_value)
    
    if results is not None:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print("\nTop Time Value Opportunities:")
        print(results)
    
if __name__ == "__main__":
    main()