if __name__ == "__main__":
    # Default values
    default_tickers = ["ORCL", "AMZN", "XOM", "SLV"]
    default_min_volume = 50
    default_max_expirations = 2
    default_min_annual_tv_pct = 9.9
    default_max_otm_pct = 5.0
    default_min_days = 5
    default_max_results = 20

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

    min_days = input(f"Enter minimum days to expiration (default: {default_min_days}): ").strip()
    min_days = int(min_days) if min_days else default_min_days

    max_results = input(f"Enter maximum number of results to display (default: {default_max_results}): ").strip()
    max_results = int(max_results) if max_results else default_max_results

    # Loop through each ticker and analyze
    for ticker in tickers:
        print(f"\nAnalyzing options for {ticker.strip()}...")
        analyze_option_chain(
            ticker_symbol=ticker.strip(),
            min_volume=min_volume,
            max_expirations=max_expirations,
            min_annual_tv_pct=min_annual_tv_pct,
            max_otm_pct=max_otm_pct,
            min_days=min_days,
            max_results=max_results
        )