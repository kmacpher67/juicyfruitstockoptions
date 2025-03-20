def analyze_option_chain(ticker_symbol, min_volume=50, max_expirations=2, 
                        min_annual_tv_pct=9.9, max_otm_pct=5.0, 
                        min_days=5, max_results=20):
    """
    Analyze option chain for a given stock ticker and find best time value opportunities
    for near-the-money call options.
    """
    print(f"\nFetching data for {ticker_symbol}...")
    print(f"Filtering for options with:")
    print(f"- Minimum annualized time value: {min_annual_tv_pct}%")
    print(f"- Maximum OTM percentage: {max_otm_pct}%")
    print(f"- Minimum volume: {min_volume}")
    print(f"- Minimum days to expiration: {min_days}")
    print(f"- Maximum results to display: {max_results}")
    
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
                
                if days_to_expiry < min_days:
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
            print(f"- Days to expiration >= {min_days}")
            return None
        
        # Convert results to DataFrame and sort
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Ann.TV%', ascending=False)
        
        # Limit the number of results displayed
        df_results = df_results.head(max_results)
        
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