"""Utilities for analysing option chains.

This module provides :func:`analyze_options` which mirrors the behaviour of
previous ad-hoc scripts but is now importable and testable.  The function
returns a :class:`pandas.DataFrame` rather than printing directly to stdout.
"""

from datetime import datetime
import time

import pandas as pd
import yfinance as yf


def get_current_price(ticker: str, retries: int = 3, delay: float = 1.0) -> float:
    """Return the most recent closing price for ``ticker``.

    Retries are attempted to mitigate transient network/API issues.  The last
    encountered exception is re-raised if all attempts fail.
    """

    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")["Close"].iloc[-1]
            if price is not None:
                return float(price)
        except Exception as exc:  # pragma: no cover - network issues
            if attempt == retries - 1:
                raise exc
            time.sleep(delay)
    raise RuntimeError(f"Unable to fetch price for {ticker}")


def analyze_options(
    ticker_symbol: str = "ORCL",
    min_volume: int = 50,
    max_expirations: int = 2,
    min_annual_tv_pct: float = 9.9,
    max_otm_pct: float = 5.0,
) -> pd.DataFrame:
    """Return call options close to the money with attractive time value."""

    current_price = get_current_price(ticker_symbol)
    max_strike = current_price * (1 + max_otm_pct / 100)
    min_strike = current_price * 0.99

    stock = yf.Ticker(ticker_symbol)
    expirations = stock.options[:max_expirations]

    results = []
    for expiry in expirations:
        opt = stock.option_chain(expiry)
        calls = opt.calls
        ntm_calls = calls[(calls["strike"] >= min_strike) & (calls["strike"] <= max_strike)]
        ntm_calls = ntm_calls[ntm_calls["volume"] >= min_volume]

        for _, option in ntm_calls.iterrows():
            days_to_expiry = (
                pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())
            ).days
            if days_to_expiry <= 0:
                continue

            if option["strike"] > current_price:
                time_value = option["lastPrice"]
            else:
                intrinsic = max(0, current_price - option["strike"])
                time_value = option["lastPrice"] - intrinsic

            time_value_pct = (time_value / option["strike"]) * (365 / days_to_expiry) * 100
            if time_value_pct >= min_annual_tv_pct:
                results.append(
                    {
                        "Expiration": expiry,
                        "Strike": option["strike"],
                        "Last": option["lastPrice"],
                        "Bid": option["bid"],
                        "Ask": option["ask"],
                        "Volume": option["volume"],
                        "OI": option["openInterest"],
                        "TimeVal$": time_value,
                        "Days": days_to_expiry,
                        "Ann.TV%": time_value_pct,
                        "Dist.%": ((option["strike"] - current_price) / current_price) * 100,
                    }
                )

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values("Ann.TV%", ascending=False)
    return df_results


def main() -> None:  # pragma: no cover - manual execution helper
    df = analyze_options()
    if not df.empty:
        pd.set_option("display.float_format", lambda x: "%.2f" % x)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(df.to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    main()
