import os
import pandas as pd
from datetime import datetime
from option_analyzer import analyze_option_chain  # Assuming option_analyzer.py is in the same directory
import yfinance as yf
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
                print(f"Retry {attempt + 1} of {max_retries} for price fetch for {ticker}...")
                time.sleep(1)
            else:
                print(f"Error: Could not fetch price for {ticker} after {max_retries} attempts. Skipping...")
                return None
    return None

def get_latest_portfolio_file(directory):
    """Find the latest portfolio file based on the date in the filename."""
    files = [f for f in os.listdir(directory) if f.startswith("portfolio.") and f.endswith(".csv")]
    files_with_dates = [(f, datetime.strptime(f.split(".")[1], "%Y%m%d")) for f in files]
    latest_file = max(files_with_dates, key=lambda x: x[1])[0]
    return os.path.join(directory, latest_file)

def evaluate_portfolio(file_path):
    """Evaluate the portfolio and provide recommendations."""
    # Read the portfolio CSV file, skipping the first row and the last 5 rows
    portfolio = pd.read_csv(file_path, skiprows=1, skipfooter=5, engine='python')

    print(f"portfolio: {portfolio}")

    # Filter for stock and option positions using the 'Security Type' column
    stock_positions = portfolio[portfolio["Security Type"] == "STK"]
    option_positions = portfolio[portfolio["Security Type"] == "OPT"]

    recommendations = []

    print("stock=" + str(stock_positions))
    print("option=" + str(option_positions))

    # Get today's date and time
    today_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Evaluate each stock position
    for _, stock in stock_positions.iterrows():
        ticker = stock["Financial Instrument Description"]
        shares = stock["Position"]
        current_price = get_current_price(ticker)
        if not current_price:
            print(f"Skipping {ticker} due to missing price data.")
            continue

        # Find related call options
        related_options = option_positions[option_positions["Financial Instrument Description"].str.contains(ticker, na=False)]
        print(f"Columns in related_options: {related_options.columns}")
        print(f"related_options DataFrame:\n{related_options}")
        total_calls_covered = related_options["Position"].abs().sum() * 100  # Each option contract covers 100 shares

        # Calculate free shares available for covered calls
        free_shares = shares - total_calls_covered

        # If there are fewer than 100 free shares, compare existing options to better alternatives
        if free_shares < 100:
            print(f"\n{ticker}: Not enough free shares for a covered call (Free Shares: {free_shares}). Comparing existing options to alternatives...")
            for _, option in related_options.iterrows():
                # Debug: Check the columns in related_options
                print(f"Columns in related_options: {related_options.columns}")
                print(f"Option row:\n{option}")

                # Analyze better alternatives for the current option
                better_options = analyze_option_chain(
                    ticker_symbol=ticker,
                    min_volume=10,
                    max_expirations=6,
                    min_annual_tv_pct=10.0,
                    max_otm_pct=10.0,
                    min_days=10,
                    max_results=5
                )

                # Check if better options are available
                if better_options is not None and not better_options.empty:
                    for better_option in better_options.to_dict(orient="records"):
                        recommendations.append({
                            "Ticker": ticker,
                            "Recommendation": "Consider Rolling to Better Option",
                            "Current Option Description": option["Financial Instrument Description"],
                            "Current Expiration": option.get("Expiration", "N/A"),
                            "Current Strike": option.get("Strike", "N/A"),  # Use fallback if missing
                            "Current Premium": option["Market Price"],
                            "New Expiration": better_option["Expiration"],
                            "New Strike": better_option["Strike"],
                            "New Premium": better_option["Last"],
                            "New Volume": better_option["Volume"],
                            "New Annualized Return (%)": better_option["Ann.TV%"],
                            "New Distance OTM (%)": better_option["Dist.%"]
                        })
            continue

        # Determine recommendation
        if total_calls_covered < shares:
            # Not fully covered, recommend selling calls
            print(f"\n{ticker}: Not fully covered. Recommending selling calls.")
            best_calls = analyze_option_chain(
                ticker_symbol=ticker,
                min_volume=10,
                max_expirations=6,
                min_annual_tv_pct=10.0,
                max_otm_pct=10.0,
                min_days=10,
                max_results=5
            )

            # Check if results are returned
            if best_calls is not None and not best_calls.empty:
                for call in best_calls.to_dict(orient="records"):
                    recommendations.append({
                        "Today's Date Time": today_datetime,
                        "Ticker": ticker,
                        "Current Option Description": "",  # Blank for new trades
                        "Recommendation": "Sell Covered Call",
                        "Expiration": call["Expiration"],
                        "Strike": call["Strike"],
                        "Premium": call["Last"],
                        "Volume": call["Volume"],
                        "Annualized Return (%)": call["Ann.TV%"],
                        "Distance OTM (%)": call["Dist.%"]
                    })
            else:
                print(f"No suitable options found for {ticker}.")
        elif total_calls_covered > shares:
            # Over-covered, recommend buying back calls
            print(f"\n{ticker}: Over-covered. Recommending buying back calls.")
            for _, option in related_options.iterrows():
                recommendations.append({
                    "Today's Date Time": today_datetime,
                    "Ticker": ticker,
                    "Current Option Description": option["Financial Instrument Description"],
                    "Recommendation": "Buy Back Call",
                    "Expiration": option["Expiration"],
                    "Strike": option["Strike"],
                    "Premium": option["Market Price"],
                    "Volume": option["Volume"],
                    "Annualized Return (%)": None,
                    "Distance OTM (%)": None
                })
        else:
            # Fully covered, recommend rolling or holding
            print(f"\n{ticker}: Fully covered. Recommending rolling or holding.")
            for _, option in related_options.iterrows():
                recommendations.append({
                    "Today's Date Time": today_datetime,
                    "Ticker": ticker,
                    "Current Option Description": option["Financial Instrument Description"],
                    "Recommendation": "Roll or Hold",
                    "Expiration": option["Expiration"],
                    "Strike": option["Strike"],
                    "Premium": option["Market Price"],
                    "Volume": option["Volume"],
                    "Annualized Return (%)": None,
                    "Distance OTM (%)": None
                })

    # Write recommendations to a CSV file
    portfolio_date = file_path.split(".")[1]  # Extract the date from the filename
    output_filename = f"recommendations.{portfolio_date}.csv"
    output_path = os.path.join(os.getcwd(), output_filename)

    # Convert recommendations to a DataFrame and write to CSV
    if recommendations:
        df_recommendations = pd.DataFrame(recommendations)
        df_recommendations.to_csv(output_path, index=False)
        print(f"\nRecommendations written to: {output_path}")
    else:
        print("\nNo recommendations to write.")

    return recommendations

if __name__ == "__main__":
    print("Portfolio Evaluator")
    # Directory containing portfolio files
    portfolio_dir = "/home/kenmac/personal/juicyfruitstockoptions"

    # Get the latest portfolio file
    latest_file = get_latest_portfolio_file(portfolio_dir)
    print(f"Processing portfolio file: {latest_file}")

    # Evaluate the portfolio
    recommendations = evaluate_portfolio(latest_file)

    # Print recommendations
    for rec in recommendations:
        print(f"\nTicker: {rec['Ticker']}")
        print(f"Recommendation: {rec['Recommendation']}")
        if rec["Details"]:
            print("Details:")
            print(pd.DataFrame(rec["Details"]))