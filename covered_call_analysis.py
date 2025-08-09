"""Analyse covered call positions from a CSV exported from a broker."""

import csv
from typing import List

import pandas as pd


def analyze_covered_calls(file_path: str) -> pd.DataFrame:
    """Return a DataFrame summarising stock and option positions.

    The function expects a CSV in the format produced by the original script.
    It calculates the number of call contracts held versus shares and flags
    whether any naked short positions exist.
    """

    with open(file_path, newline="") as f:
        all_lines = list(csv.reader(f))

    stock_lines = [
        row[:7]
        for row in all_lines
        if len(row) >= 7 and row[0] == "Open Positions" and row[1] == "Data" and row[2] == "Stocks"
    ]
    df_stocks = pd.DataFrame(
        stock_lines, columns=["Section", "Header", "Asset Category", "Currency", "Symbol", "Account", "Quantity"]
    )
    df_stocks["Quantity"] = pd.to_numeric(df_stocks["Quantity"], errors="coerce")
    df_stocks["Account"] = df_stocks["Account"].fillna("DEFAULT")
    df_stocks["Symbol"] = df_stocks["Symbol"].str.strip()
    stock_holdings = df_stocks.groupby(["Symbol", "Account"])["Quantity"].sum().reset_index()
    stock_holdings.rename(columns={"Quantity": "Shares Held"}, inplace=True)

    option_lines = [
        row
        for row in all_lines
        if len(row) >= 7 and row[0] == "Open Positions" and row[1] == "Data" and row[2] == "Equity and Index Options"
    ]
    if option_lines:
        df_options = pd.DataFrame(option_lines, columns=[f"col_{i}" for i in range(len(option_lines[0]))])
        df_options.rename(columns={"col_4": "Symbol", "col_5": "Account", "col_6": "Quantity"}, inplace=True)
        df_options["Quantity"] = pd.to_numeric(df_options["Quantity"], errors="coerce")
        df_options["Account"] = df_options["Account"].fillna("DEFAULT")
        df_options["Underlying"] = df_options["Symbol"].apply(lambda x: x.split(" ")[0].strip())
        short_calls = df_options[df_options["Quantity"] < 0]
        short_calls_summary = short_calls.groupby(["Underlying", "Account"])["Quantity"].sum().reset_index()
        short_calls_summary.rename(columns={"Underlying": "Symbol", "Quantity": "Call Contracts Held"}, inplace=True)
    else:
        short_calls_summary = pd.DataFrame(columns=["Symbol", "Account", "Call Contracts Held"])

    df = pd.merge(stock_holdings, short_calls_summary, on=["Symbol", "Account"], how="outer")
    df["Shares Held"] = df["Shares Held"].fillna(0)
    df["Call Contracts Held"] = df["Call Contracts Held"].fillna(0)
    df["Calls Available to Sell"] = (df["Shares Held"] // 100 + df["Call Contracts Held"]).astype(int)
    df["Naked Short?"] = df["Calls Available to Sell"] < 0
    return df


__all__ = ["analyze_covered_calls"]
