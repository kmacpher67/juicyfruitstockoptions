import os
import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np
import traceback
import time

def get_current_price(ticker):
    """Fetch the current stock price with retries."""
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
                time.sleep(2 + attempt )
            else:
                raise Exception(f"Could not fetch price for {ticker} after {max_retries} attempts: {str(e)}")
    return None


def analyze_option_chain(ticker_symbol, min_volume=100, max_expirations=6, min_annual_tv_pct=10.9, max_otm_pct=15.0,
                         min_days=10, max_results=5, portfolio_date=None, minimum_bid_amount=0):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for near-the-money call options.
    
    Args:
        ticker_symbol (str): Stock symbol
        min_volume (int): Minimum option volume default is 100
        max_expirations (int): Number of expiration dates to analyze
        min_annual_tv_pct (float): Minimum annualized time value percentage
        max_otm_pct (float): Maximum percentage out-of-the-money to consider
        min_days (int): Minimum days to expiration
        max_results (int): Maximum number of results to display
        portfolio_date (str): Date of the portfolio in YYYYMMDD format (used for output filename)
        minimum_bid_amount (int): Minimum bid price to consider
    """
    print(f"\nFetching data for {ticker_symbol}...")
    print(f"Filtering for options with:")
    print(f"- Minimum annualized time value: {min_annual_tv_pct}%")
    print(f"- Maximum OTM percentage: {max_otm_pct}%")
    print(f"- Minimum volume: {min_volume}")
    print(f"- Minimum days to expiration: {min_days}")
    print(f"- Minimum bid amount: {minimum_bid_amount}")
    print(f"- Max results to display: {max_results}")
    
    try:
        # Get current stock price using simplified method
        current_price = get_current_price(ticker_symbol)
        if not current_price:
            print(f"Error: Could not fetch current price for {ticker_symbol}")
            return
        
        print(f"\nCurrent Price: ${current_price:.2f}")
        
        # Calculate price range for near-the-money options
        max_strike = current_price * (1 + max_otm_pct / 100)
        min_strike = current_price * 0.98  # Consider options just slightly ITM
        
        print(f"Analyzing strikes between ${min_strike:.2f} and ${max_strike:.2f}")
        
        # Get stock object
        stock = yf.Ticker(ticker_symbol)
        
        # Get expiration dates
        all_expirations = stock.options
        if not all_expirations:
            print("No options data available")
            return
        
        # Filter expiration dates based on min_days
        today = datetime.now().date()
        valid_expirations = [
            expiry for expiry in all_expirations
            if (pd.to_datetime(expiry).date() - today).days > min_days
        ]
        
        if not valid_expirations:
            print(f"No expiration dates found with more than {min_days} days to expiration.")
            return
        
        # Limit to max_expirations
        expirations = valid_expirations[:max_expirations]
        print(f"Analyzing {len(expirations)} expiration dates")
        
        results = []
        
        # Analyze each expiration date
        for expiry in expirations:
            print(f"\nProcessing {expiry}...")
            
            # Get option chain
            opt = stock.option_chain(expiry)
            calls = opt.calls

            # Filter for near-the-money calls
            ntm_calls = calls[
                (calls['strike'] >= min_strike) & 
                (calls['strike'] <= max_strike)
            ]
            
            # Filter for minimum volume and minimum bid amount
            ntm_calls = ntm_calls[
                (ntm_calls['volume'] >= min_volume) & 
                (ntm_calls['bid'] >= minimum_bid_amount)
            ]
            
            if len(ntm_calls) == 0:
                print(f"No suitable options found for {expiry}")
                continue
            
            # Calculate metrics for each option
            for _, option in ntm_calls.iterrows():
                days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(today)).days
                
                if days_to_expiry <= 0:
                    continue
                
                # Calculate time value out of the money
                if option['strike'] > current_price:
                    # OTM option - all premium is time value
                    time_value = option['lastPrice']
                else:
                    # ITM option - subtract intrinsic value (in the money exercise value)
                    intrinsic = max(0, current_price - option['strike'])
                    time_value = option['lastPrice'] + option['strike']
                
                # Calculate annualized time value percentage
                time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
                
                # Only include if meets minimum time value percentage
                if time_value_pct >= min_annual_tv_pct:
                    results.append({
                        'Expiration': expiry,
                        'Strike': option['strike'],
                        'Last': option['lastPrice'],
                        'Bid': option['bid'],
                        'Ask': option['ask'],
                        'Volume': option['volume'],
                        'OI': option['openInterest'],
                        'TimeVal$': time_value,
                        'Days': days_to_expiry,
                        'Ann.TV%': time_value_pct,
                        'Dist.%': ((option['strike'] - current_price) / current_price) * 100
                    })
        
        if not results:
            print("\nNo options found matching the criteria:")
            print(f"- Annualized time value >= {min_annual_tv_pct}%")
            print(f"- Within {max_otm_pct}% of current price")
            print(f"- Volume >= {min_volume}")
            print(f"- Bid >= {minimum_bid_amount}")
            return
        
        # Convert results to DataFrame and sort
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Ann.TV%', ascending=False)
        
        # Apply max_results limit
        if max_results > 0:
            print ("limit max results to", max_results)
            df_results = df_results.head(max_results)
        
        # Print results
        print("\nBest Time Value Opportunities (sorted by annualized time value):")
        print("=========================================================")
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_results.to_string(index=False))
        
        # Write results to a CSV file
        if portfolio_date:
            output_filename = f"recommendations.{portfolio_date}.csv"
        elif ticker_symbol:
            output_filename = f"recommendations.{ticker_symbol}.csv"
        else:
            output_filename = f"recommendations.csv"
        
        output_path = os.path.join(os.getcwd(), output_filename)
        df_results.to_csv(output_path, index=False)
        print(f"\nRecommendations written to: {output_path}")
        
        return df_results
        
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            last_call = tb[-1]
            print(f"Error in analysis: {e} (Line {last_call.lineno} in {last_call.filename})")
        else:
            print(f"Error in analysis: {e}")
        return None

def main():
    ticker = input("Enter stock ticker symbol (e.g., ORCL): ").upper()
    min_vol = int(input("Enter minimum option volume (default 100): ") or "100")
    portfolio_date = input("Enter portfolio date in YYYYMMDD format (optional): ")
    min_days = int(input("Enter minimum days to expiration (default 10): ") or "10")
    min_bid = float(input("Enter minimum bid amount (default 0): ") or "0")
    min_annual_tv_pct = float(input("Enter minimum annualized time value percentage (default 10.9): ") or "10.9")    
    max_expirations = int(input("Enter maximum expiration dates to analyze (default 5): ") or "5")
    max_otm_pct = float(input("Enter maximum OTM percentage (default 16.0): ") or "16.0")
    max_results = int(input("Enter maximum number of results to display (default 5): ") or "7")
    
    analyze_option_chain(ticker, min_vol, max_expirations, min_annual_tv_pct=min_annual_tv_pct, max_otm_pct=max_otm_pct, min_days=min_days, max_results=max_results, portfolio_date=portfolio_date, minimum_bid_amount=min_bid)

if __name__ == "__main__":
    main()