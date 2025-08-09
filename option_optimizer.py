"""Option optimisation utilities.

Refactored from a script that previously performed all work at the top level
and printed results.  The primary entry point is :func:`optimize_options` which
returns a :class:`pandas.DataFrame` of qualifying options.
"""

from datetime import datetime
import time
from typing import Iterable

import pandas as pd
import yfinance as yf


def get_current_price(ticker: str, retries: int = 3, delay: float = 1.0) -> float:
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")["Close"].iloc[-1]
            if price is not None:
                return float(price)
        except Exception as exc:  # pragma: no cover
            if attempt == retries - 1:
                raise exc
            time.sleep(delay)
    raise RuntimeError(f"Unable to fetch price for {ticker}")


def optimize_options(
    ticker_symbol: str,
    min_volume: int = 50,
    max_expirations: int = 2,
    min_annual_tv_pct: float = 9.9,
    max_otm_pct: float = 5.0,
    min_days: int = 5,
    max_results: int = 20,
) -> pd.DataFrame:
    """Return near-the-money call options ordered by annualised time value."""

    current_price = get_current_price(ticker_symbol)
    max_strike = current_price * (1 + max_otm_pct / 100)
    min_strike = current_price * 0.99

    stock = yf.Ticker(ticker_symbol)
    expirations = stock.options[:max_expirations]

    rows = []
    for expiry in expirations:
        opt = stock.option_chain(expiry)
        calls = opt.calls
        ntm = calls[(calls["strike"] >= min_strike) & (calls["strike"] <= max_strike)]
        ntm = ntm[ntm["volume"] >= min_volume]

        for _, option in ntm.iterrows():
            days = (pd.to_datetime(expiry) - pd.to_datetime(datetime.now().date())).days
            if days <= 0 or days < min_days:
                continue
            if option["strike"] > current_price:
                time_value = option["lastPrice"]
            else:
                intrinsic = max(0, current_price - option["strike"])
                time_value = option["lastPrice"] - intrinsic
            time_value_pct = (time_value / option["strike"]) * (365 / days) * 100
            if time_value_pct >= min_annual_tv_pct:
                rows.append(
                    {
                        "Ticker": ticker_symbol,
                        "Expiration": expiry,
                        "Strike": option["strike"],
                        "Last": option["lastPrice"],
                        "Bid": option["bid"],
                        "Ask": option["ask"],
                        "Volume": option["volume"],
                        "OI": option["openInterest"],
                        "TimeVal$": time_value,
                        "Days": days,
                        "Ann.TV%": time_value_pct,
                        "Dist.%": ((option["strike"] - current_price) / current_price) * 100,
                    }
                )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Ann.TV%", ascending=False).head(max_results)
    return df


def main() -> None:  # pragma: no cover
    df = optimize_options("ORCL")
    if not df.empty:
        pd.set_option("display.float_format", lambda x: "%.2f" % x)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(df.to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    main()
