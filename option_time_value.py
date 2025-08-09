import pandas as pd
from option_analyzers import TimeValueAnalyzer


def main():
    default_tickers = ["ORCL", "AMZN", "XOM"]
    user_input = input(
        f"Enter stock tickers separated by comma (default: {','.join(default_tickers)}): "
    ).strip()
    tickers = (
        [t.strip().upper() for t in user_input.split(',')] if user_input else default_tickers
    )

    while True:
        try:
            min_time_value = float(input("Enter minimum time value (default: 0.10): ") or 0.10)
            break
        except ValueError:
            print("Please enter a valid number")

    analyzer = TimeValueAnalyzer()
    print("\nAnalyzing options... This may take a moment.")
    results = analyzer.analyze(tickers=tickers, min_time_value=min_time_value)

    if results is not None:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print("\nTop Time Value Opportunities:")
        print(results)


if __name__ == "__main__":
    main()

