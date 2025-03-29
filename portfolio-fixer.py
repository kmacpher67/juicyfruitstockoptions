import os
import pandas as pd
from datetime import datetime
from option_analyzer import analyze_option_chain  # Assuming option_analyzer.py is in the same directory

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

    # Evaluate each stock position
    for _, stock in stock_positions.iterrows():
        ticker = stock["Financial Instrument Description"]
        shares = stock["Position"]
        current_price = stock["Market Price"]

        # Find related call options
        related_options = option_positions[option_positions["Financial Instrument Description"].str.contains(ticker, na=False)]
        total_calls_covered = related_options["Position"].abs().sum() * 100  # Each option contract covers 100 shares

        # Calculate free shares available for covered calls
        free_shares = shares - total_calls_covered

        # Skip if there are fewer than 100 free shares
        if free_shares < 100:
            print(f"\n{ticker}: Not enough free shares for a covered call (Free Shares: {free_shares}). Skipping...")
            continue

        # Determine recommendation
        if total_calls_covered < shares:
            # Not fully covered, recommend selling calls
            print(f"\n{ticker}: Not fully covered. Recommending selling calls.")
            best_calls = analyze_option_chain(
                ticker_symbol=ticker,
                min_volume=50,
                max_expirations=6,
                min_annual_tv_pct=12.0,
                max_otm_pct=5.0,
                min_days=10,
                max_results=5
            )

            # Check if results are returned
            if best_calls is not None and not best_calls.empty:
                for call in best_calls.to_dict(orient="records"):
                    recommendations.append({
                        "Ticker": ticker,
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
                    "Ticker": ticker,
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
                    "Ticker": ticker,
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