import yfinance as yf
import pandas as pd
from datetime import datetime
import time
from datetime import datetime, date

def calculate_days_to_expiration(expiration_date):
    """Calculate the number of days between now and expiration"""
    exp_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
    today = date.today()
    return (exp_date - today).days

def get_option_chain(ticker, max_expiration_dates):
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
            
        # Limit the number of expiration dates
        dates = dates[:max_expiration_dates]
        
        all_calls = []
        for date in dates:
            try:
                opt = stock.option_chain(date)
                calls = opt.calls
                calls['expirationDate'] = date
                calls['stockPrice'] = current_price
                calls['daysToExpiration'] = calculate_days_to_expiration(date)
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

def calculate_metrics(row):
    """
    Calculate time value and annualized return
    """
    intrinsic_value = max(0, row['stockPrice'] - row['strike'])
    time_value = row['lastPrice'] - intrinsic_value
    
    # Calculate investment required (option cost or strike price depending on strategy)
    investment = row['lastPrice'] * 100  # Convert to contract size
    
    # Calculate annualized return
    if row['daysToExpiration'] > 0:
        annualized_return = (time_value * 100 * 365) / (investment * row['daysToExpiration']) * 100
    else:
        annualized_return = 0
        
    return pd.Series({
        'timeValue': time_value,
        'annualizedReturn': annualized_return
    })

def analyze_options(tickers=["ORCL", "AMZN", "XOM"], 
                   min_annual_return=11,
                   min_volume=20,
                   max_expiration_dates=4,
                   max_otm_pct=10):
    """
    Analyze options for multiple tickers and find best time value opportunities
    """
    all_opportunities = []
    
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...")
        option_chain, current_price, ticker_name = get_option_chain(ticker, max_expiration_dates)
        
        if option_chain is None:
            continue
            
        # Filter for OTM calls
        otm_calls = option_chain[option_chain['strike'] > current_price].copy()
        
        if len(otm_calls) == 0:
            continue
            
        # Calculate OTM percentage
        otm_calls['percentOTM'] = ((otm_calls['strike'] - current_price) / current_price) * 100
        
        # Apply initial filters
        filtered_calls = otm_calls[
            (otm_calls['percentOTM'] <= max_otm_pct) &
            (otm_calls['volume'] >= min_volume)
        ].copy()
        
        if len(filtered_calls) == 0:
            continue
            
        # Calculate metrics
        metrics = filtered_calls.apply(calculate_metrics, axis=1)
        filtered_calls['timeValue'] = metrics['timeValue']
        filtered_calls['annualizedReturn'] = metrics['annualizedReturn']
        
        # Filter by minimum annualized return
        good_opportunities = filtered_calls[
            filtered_calls['annualizedReturn'] >= min_annual_return
        ].copy()
        
        if len(good_opportunities) > 0:
            good_opportunities['ticker'] = ticker_name
            all_opportunities.append(good_opportunities)
    
    if not all_opportunities:
        print("No opportunities found matching criteria")
        return None
        
    # Combine all opportunities
    all_df = pd.concat(all_opportunities)
    
    # Select and rename relevant columns
    result = all_df[[
        'ticker', 'expirationDate', 'strike', 'lastPrice', 'timeValue',
        'annualizedReturn', 'percentOTM', 'volume', 'openInterest',
        'daysToExpiration'
    ]].copy()
    
    # Sort by annualized return descending
    result = result.sort_values('annualizedReturn', ascending=False)
    
    # Format the results
    result['percentOTM'] = result['percentOTM'].round(2)
    result['timeValue'] = result['timeValue'].round(2)
    result['strike'] = result['strike'].round(2)
    result['lastPrice'] = result['lastPrice'].round(2)
    result['annualizedReturn'] = result['annualizedReturn'].round(2)
    
    # Limit to top 15 opportunities
    return result.head(15)

def main():
    # Get user input for tickers
    default_tickers = ["ORCL", "AMZN", "XOM"]
    user_input = input(f"Enter stock tickers separated by comma (default: {','.join(default_tickers)}): ").strip()
    
    if user_input:
        tickers = [ticker.strip().upper() for ticker in user_input.split(',')]
    else:
        tickers = default_tickers
    
    # Get minimum annualized return
    while True:
        try:
            min_annual_return = float(input("Enter minimum annualized return % (default: 11): ") or 11)
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Get minimum volume
    while True:
        try:
            min_volume = int(input("Enter minimum option volume (default: 20): ") or 20)
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Get maximum expiration dates
    while True:
        try:
            max_expiration_dates = int(input("Enter maximum number of expiration dates to analyze (default: 4): ") or 4)
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Get maximum OTM percentage
    while True:
        try:
            max_otm_pct = float(input("Enter maximum OTM percentage (default: 10): ") or 10)
            break
        except ValueError:
            print("Please enter a valid number")
    
    print("\nAnalyzing options... This may take a moment.")
    results = analyze_options(
        tickers=tickers,
        min_annual_return=min_annual_return,
        min_volume=min_volume,
        max_expiration_dates=max_expiration_dates,
        max_otm_pct=max_otm_pct
    )
    
    if results is not None:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print("\nTop 15 Time Value Opportunities (Sorted by Annualized Return):")
        print(results)
        
        # Print summary of filters applied
        print("\nFilters applied:")
        print(f"- Minimum annualized return: {min_annual_return}%")
        print(f"- Minimum volume: {min_volume}")
        print(f"- Maximum OTM percentage: {max_otm_pct}%")
        print(f"- Number of expiration dates analyzed: {max_expiration_dates}")
    
if __name__ == "__main__":
    main()