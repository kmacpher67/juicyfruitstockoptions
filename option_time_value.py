"""Time value calculations for option chains.

The original script mixed user interaction and printing with the core logic.
This refactored module exposes reusable functions that return data structures
for use elsewhere.
"""

import time
from typing import Iterable, List, Tuple

import pandas as pd
import yfinance as yf


def get_option_chain(ticker: str) -> Tuple[pd.DataFrame, float, str]:
    """Return a concatenated call option chain for ``ticker``.

    Only the first three expiration dates are retrieved to limit API calls.
    The returned DataFrame contains additional ``expirationDate`` and
    ``stockPrice`` columns.
    """

    stock = yf.Ticker(ticker)
    time.sleep(1)
    current_price = stock.info["regularMarketPrice"]
    dates = stock.options[:3]

    all_calls: List[pd.DataFrame] = []
    for date in dates:
        opt = stock.option_chain(date)
        calls = opt.calls
        calls["expirationDate"] = date
        calls["stockPrice"] = current_price
        all_calls.append(calls)
        time.sleep(1)

    if not all_calls:
        return pd.DataFrame(), current_price, ticker
    return pd.concat(all_calls), current_price, ticker


def calculate_time_value(row: pd.Series) -> float:
    """Return the time value for a single option row."""

    intrinsic_value = max(0, row["stockPrice"] - row["strike"])
    return row["lastPrice"] - intrinsic_value


def analyze_options(
    tickers: Iterable[str], min_time_value: float = 0.10
) -> pd.DataFrame:
    """Return out-of-the-money call options with at least ``min_time_value``."""

    opportunities: List[pd.DataFrame] = []
    for ticker in tickers:
        option_chain, current_price, ticker_name = get_option_chain(ticker)
        if option_chain.empty:
            continue
        otm_calls = option_chain[option_chain["strike"] > current_price].copy()
        if otm_calls.empty:
            continue
        otm_calls["timeValue"] = otm_calls.apply(calculate_time_value, axis=1)
        good = otm_calls[otm_calls["timeValue"] >= min_time_value].copy()
        if not good.empty:
            good["ticker"] = ticker_name
            good["percentOTM"] = ((good["strike"] - current_price) / current_price) * 100
            opportunities.append(good)

    if not opportunities:
        return pd.DataFrame()

    all_df = pd.concat(opportunities)
    result = all_df[
        [
            "ticker",
            "expirationDate",
            "strike",
            "lastPrice",
            "timeValue",
            "percentOTM",
            "volume",
            "openInterest",
        ]
    ].copy()
    result = result.sort_values("timeValue", ascending=False)
    result["percentOTM"] = result["percentOTM"].round(2)
    result["timeValue"] = result["timeValue"].round(2)
    result["strike"] = result["strike"].round(2)
    result["lastPrice"] = result["lastPrice"].round(2)
    return result


__all__ = [
    "get_option_chain",
    "calculate_time_value",
    "analyze_options",
]
