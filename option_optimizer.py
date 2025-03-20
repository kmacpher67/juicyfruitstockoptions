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

def analyze_option_chain(ticker_symbol, min_volume=50, max_expirations=2, 
                        min_annual_tv_pct=9.9, max_otm_pct=5.0):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for near-the-money call options.
    """
    print(f"\nFetching data for {ticker_symbol}...")
    print(f"Filtering for options with:")
    print(f"- Minimum annualized time value: {min_annual_tv_pct}%")
    print(f"- Maximum OTM percentage: {max_otm_pct}%")
    print(f"- Minimum volume: {min_volume}")
    
    try:
        # Get current stock price
        current_price = get_current_price(ticker_symbol)
        if not current_price:
            print(f"Error: Could not fetch current price for {ticker_symbol}")
            return None
        
        print(f"\nCurrent Price: ${current_price:.2f}")
        
        # Calculate price range for near-the-money options
        max_strike = current_price * (1 + max_otm_pct/100)
        min_strike = current_price * 0.99  # Consider options just slightly ITM
        
        print(f"Analyzing strikes between ${min_strike:.2f} and ${max_strike:.2f}")
        
        # Get stock object
        stock = yf.Ticker(ticker_symbol)
        
        # Get expiration dates
        all_expirations = stock.options
        if not all_expirations:
            print("No options data available")
            return None
            
        expirations = all_expirations[:max_expirations]
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
            
            # Filter for minimum volume
            ntm_calls = ntm_calls[ntm_calls['volume'] >= min_volume]
            
            if len(ntm_calls) == 0:
                print(f"No suitable options found for {expiry}")
                continue
            
            # Calculate metrics for each option
            for _, option in ntm_calls.iterrows():
                days_to_expiry = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
                
                if days_to_expiry <= 0:
                    continue
                
                # Calculate time value
                if option['strike'] > current_price:
                    # OTM option - all premium is time value
                    time_value = option['lastPrice']
                else:
                    # ITM option - subtract intrinsic value
                    intrinsic = max(0, current_price - option['strike'])
                    time_value = option['lastPrice'] - intrinsic
                
                # Calculate annualized time value percentage
                time_value_pct = (time_value / option['strike']) * (365 / days_to_expiry) * 100
                
                # Only include if meets minimum time value percentage
                if time_value_pct >= min_annual_tv_pct:
                    results.append({
                        'Ticker': ticker_symbol,
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
            return None
        
        # Convert results to DataFrame and sort
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Ann.TV%', ascending=False)
        
        # Print results
        print("\nBest Time Value Opportunities (sorted by annualized time value):")
        print("=========================================================")
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_results.to_string(index=False))
        
        return df_results
        
    except Exception as e:
        print(f"Error in analysis for {ticker_symbol}: {str(e)}")
        return None

if __name__ == "__main__":
    # Default values
    default_tickers = ["ORCL", "AMZN", "XOM", "SLV"]
    default_min_volume = 50
    default_max_expirations = 2
    default_min_annual_tv_pct = 9.9
    default_max_otm_pct = 5.0

    # User input
    tickers_input = input(f"Enter stock tickers (comma-separated, default: {default_tickers}): ").strip()
    tickers = tickers_input.split(",") if tickers_input else default_tickers

    min_volume = input(f"Enter minimum volume (default: {default_min_volume}): ").strip()
    min_volume = int(min_volume) if min_volume else default_min_volume

    max_expirations = input(f"Enter maximum expiration dates to analyze (default: {default_max_expirations}): ").strip()
    max_expirations = int(max_expirations) if max_expirations else default_max_expirations

    min_annual_tv_pct = input(f"Enter minimum annualized time value percentage (default: {default_min_annual_tv_pct}): ").strip()
    min_annual_tv_pct = float(min_annual_tv_pct) if min_annual_tv_pct else default_min_annual_tv_pct

    max_otm_pct = input(f"Enter maximum OTM percentage (default: {default_max_otm_pct}): ").strip()
    max_otm_pct = float(max_otm_pct) if max_otm_pct else default_max_otm_pct

    # Loop through each ticker and analyze
    for ticker in tickers:
        print(f"\nAnalyzing options for {ticker.strip()}...")
        analyze_option_chain(
            ticker_symbol=ticker.strip(),
            min_volume=min_volume,
            max_expirations=max_expirations,
            min_annual_tv_pct=min_annual_tv_pct,
            max_otm_pct=max_otm_pct
        )