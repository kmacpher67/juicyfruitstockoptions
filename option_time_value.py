"""Time value calculations for option chains.

This module provides functional helpers used by the tests while delegating
the heavy lifting to :class:`TimeValueAnalyzer` in :mod:`option_analyzers`.
"""

from typing import Iterable, Tuple

import pandas as pd
import yfinance as yf

from option_analyzers import TimeValueAnalyzer


def get_option_chain(ticker: str) -> Tuple[pd.DataFrame, float, str]:
    """Return a concatenated call option chain for ``ticker``."""
    analyzer = TimeValueAnalyzer(yf_module=yf)
    return analyzer.get_option_chain(ticker)


def calculate_time_value(row: pd.Series) -> float:
    """Return the time value for a single option row."""
    return TimeValueAnalyzer.calculate_time_value(row)


def analyze_options(tickers: Iterable[str], min_time_value: float = 0.10) -> pd.DataFrame:
    """Return out-of-the-money call options with at least ``min_time_value``."""
    analyzer = TimeValueAnalyzer(yf_module=yf)
    result = analyzer.analyze(list(tickers), min_time_value)
    return result if result is not None else pd.DataFrame()


def main() -> None:  # pragma: no cover - CLI helper
    default_tickers = ["ORCL", "AMZN", "XOM"]
    user_input = input(
        f"Enter stock tickers separated by comma (default: {','.join(default_tickers)}): "
    ).strip()
    tickers = [t.strip().upper() for t in user_input.split(',')] if user_input else default_tickers

    while True:
        try:
            min_time_value = float(input("Enter minimum time value (default: 0.10): ") or 0.10)
            break
        except ValueError:
            print("Please enter a valid number")

    print("\nAnalyzing options... This may take a moment.")
    results = analyze_options(tickers=tickers, min_time_value=min_time_value)

    if not results.empty:
        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print("\nTop Time Value Opportunities:")
        print(results)


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["get_option_chain", "calculate_time_value", "analyze_options"]

