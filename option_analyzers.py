import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
import yfinance as yf


class BaseOptionAnalyzer(ABC):
    """Shared utilities for option analysis."""

    def __init__(self, yf_module=yf):
        self.yf = yf_module

    def get_current_price(self, ticker: str, max_retries: int = 3) -> float:
        """Fetch the current stock price with retries."""
        for attempt in range(max_retries):
            try:
                stock = self.yf.Ticker(ticker)
                price = stock.history(period="1d")["Close"].iloc[-1]
                if price:
                    return price
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1 + attempt)
                else:
                    raise
        raise RuntimeError(f"Failed to fetch price for {ticker}")

    @abstractmethod
    def analyze(self, *args, **kwargs):
        """Run the option analysis and return a DataFrame."""
        raise NotImplementedError


class OptionChainAnalyzer(BaseOptionAnalyzer):
    """Find near-the-money call options with high time value."""

    def analyze(
        self,
        ticker_symbol: str,
        min_volume: int = 50,
        max_expirations: int = 2,
        min_annual_tv_pct: float = 9.9,
        max_otm_pct: float = 5.0,
    ) -> Optional[pd.DataFrame]:
        current_price = self.get_current_price(ticker_symbol)
        max_strike = current_price * (1 + max_otm_pct / 100)
        min_strike = current_price * 0.99

        stock = self.yf.Ticker(ticker_symbol)
        all_expirations = stock.options
        if not all_expirations:
            return None
        expirations = all_expirations[:max_expirations]

        results = []
        for expiry in expirations:
            calls = stock.option_chain(expiry).calls
            ntm_calls = calls[(calls["strike"] >= min_strike) & (calls["strike"] <= max_strike)]
            ntm_calls = ntm_calls[ntm_calls["volume"] >= min_volume]
            if ntm_calls.empty:
                continue
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
                time_value_pct = (
                    time_value / option["strike"] * (365 / days_to_expiry) * 100
                )
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
                            "Dist.%": ((option["strike"] - current_price) / current_price)
                            * 100,
                        }
                    )
        if not results:
            return None
        df_results = pd.DataFrame(results).sort_values("Ann.TV%", ascending=False)
        return df_results


class TimeValueAnalyzer(BaseOptionAnalyzer):
    """Analyze multiple tickers for out-of-the-money call time value."""

    @staticmethod
    def calculate_time_value(row: pd.Series) -> float:
        """Return the time value for a single option row."""
        intrinsic = max(0, row["stockPrice"] - row["strike"])
        return row["lastPrice"] - intrinsic

    def get_option_chain(self, ticker: str) -> Tuple[pd.DataFrame, float, str]:
        stock = self.yf.Ticker(ticker)
        current_price = stock.info.get("regularMarketPrice")
        dates = stock.options[:3]
        all_calls: List[pd.DataFrame] = []
        for date in dates:
            try:
                calls = stock.option_chain(date).calls
                calls["expirationDate"] = date
                calls["stockPrice"] = current_price
                all_calls.append(calls)
                time.sleep(1)
            except Exception as e:
                print(f"Error getting option chain for {ticker} {date}: {e}")
        if not all_calls:
            return pd.DataFrame(), current_price, ticker
        return pd.concat(all_calls), current_price, ticker

    def analyze(
        self, tickers: Optional[List[str]] = None, min_time_value: float = 0.10
    ) -> Optional[pd.DataFrame]:
        tickers = tickers or ["ORCL", "AMZN", "XOM"]
        all_opportunities = []
        for ticker in tickers:
            option_chain, current_price, ticker_name = self.get_option_chain(ticker)
            if option_chain.empty:
                continue
            otm_calls = option_chain[option_chain["strike"] > current_price].copy()
            if otm_calls.empty:
                continue
            otm_calls["timeValue"] = otm_calls.apply(self.calculate_time_value, axis=1)
            good = otm_calls[otm_calls["timeValue"] >= min_time_value].copy()
            if not good.empty:
                good["ticker"] = ticker_name
                good["percentOTM"] = (
                    (good["strike"] - current_price) / current_price * 100
                )
                all_opportunities.append(good)
        if not all_opportunities:
            return None
        all_df = pd.concat(all_opportunities)
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
