"""Utilities for analysing option chains.

This module exposes :func:`analyze_options`, a thin wrapper around
``OptionChainAnalyzer`` from :mod:`option_analyzers` to keep the
implementation reusable while providing a simple functional API.
"""

from option_analyzers import OptionChainAnalyzer
import pandas as pd
import yfinance as yf


def analyze_options(
    ticker_symbol: str = "ORCL",
    min_volume: int = 50,
    max_expirations: int = 2,
    min_annual_tv_pct: float = 9.9,
    max_otm_pct: float = 5.0,
) -> pd.DataFrame:
    """Return call options close to the money with attractive time value."""

    analyzer = OptionChainAnalyzer(yf_module=yf)
    df = analyzer.analyze(
        ticker_symbol=ticker_symbol,
        min_volume=min_volume,
        max_expirations=max_expirations,
        min_annual_tv_pct=min_annual_tv_pct,
        max_otm_pct=max_otm_pct,
    )
    return df if df is not None else pd.DataFrame()


def main() -> None:  # pragma: no cover - manual execution helper
    df = analyze_options()
    if not df.empty:
        pd.set_option("display.float_format", lambda x: "%.2f" % x)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(df.to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    main()

