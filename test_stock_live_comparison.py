import pandas as pd
from datetime import datetime, timedelta
from stock_live_comparison import StockLiveComparison

## Component Test cases for StockLiveComparison class
## Test checks if output files are created correctly and contain expected data.
def test_run_creates_spreadsheet(tmp_path):
    tickers = ["AAPL", "MSFT"]
    comp = StockLiveComparison(tickers)
    comp.output_dir = tmp_path
    comp.run()
    files = list(tmp_path.glob("*.xlsx"))
    assert len(files) > 0

def test_run_with_empty_tickers(tmp_path):
    comp = StockLiveComparison([])
    comp.output_dir = tmp_path
    comp.run()
    files = list(tmp_path.glob("*.xlsx"))
    assert len(files) > 0

def test_run_handles_invalid_ticker(tmp_path):
    tickers = ["INVALIDTICKER"]
    comp = StockLiveComparison(tickers)
    comp.output_dir = tmp_path
    comp.run()
    files = list(tmp_path.glob("*.xlsx"))
    assert len(files) > 0

def test_spreadsheet_contains_last_update(tmp_path):
    tickers = ["AAPL"]
    comp = StockLiveComparison(tickers)
    comp.output_dir = tmp_path
    comp.run()
    files = list(tmp_path.glob("*.xlsx"))
    df = pd.read_excel(files[0])
    assert "Last Update" in df.columns

def test_get_missing_or_outdated_tickers():
    tickers = ["AAPL", "MSFT", "GOOG"]
    comp = StockLiveComparison(tickers)
    now = datetime.now()
    old_time = (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    recent_time = now.strftime("%Y-%m-%d %H:%M:%S")
    # Simulate existing DataFrame
    df_existing = pd.DataFrame([
        {"Ticker": "AAPL", "Last Update": recent_time},
        {"Ticker": "MSFT", "Last Update": old_time},
        {"Ticker": "GOOG", "Last Update": None},
    ])
    missing_or_old = comp.get_missing_or_outdated_tickers(df_existing)
    # Only MSFT and GOOG should be considered missing or outdated
    assert set(missing_or_old) == {"MSFT", "GOOG"}

def test_add_ratio_column_handles_existing_column():
    import pandas as pd
    from stock_live_comparison import StockLiveComparison
    comp = StockLiveComparison(["AAPL"])
    df = pd.DataFrame({
        "Annual Yield Put Prem": [10, 20],
        "Annual Yield Call Prem": [5, 0],
        "Put/Call Yield Ratio": [2, None]  # Already exists
    })
    # Should not crash, should print error, and should return df unchanged
    df2, put_col, call_col = comp.add_ratio_column(df)
    assert "Put/Call Yield Ratio" in df2.columns
    # The values should be updated for valid rows
    assert df2["Put/Call Yield Ratio"].iloc[0] == 2
    assert pd.isna(df2["Put/Call Yield Ratio"].iloc[1])

def test_upsert_ratio_column_idempotent_and_error_handling(capfd):
    import pandas as pd
    from stock_live_comparison import StockLiveComparison
    comp = StockLiveComparison(["AAPL"])
    # Case 1: Column does not exist
    df = pd.DataFrame({
        "Annual Yield Put Prem": [10, 20],
        "Annual Yield Call Prem": [5, 0]
    })
    df2 = comp.upsert_ratio_column(df)
    assert "Put/Call Yield Ratio" in df2.columns
    assert df2["Put/Call Yield Ratio"].iloc[0] == 2
    assert pd.isna(df2["Put/Call Yield Ratio"].iloc[1])
    out, _ = capfd.readouterr()
    assert 'Column "Put/Call Yield Ratio" inserted.' in out

    # Case 2: Column already exists
    df3 = pd.DataFrame({
        "Annual Yield Put Prem": [10, 20],
        "Annual Yield Call Prem": [5, 0],
        "Put/Call Yield Ratio": [None, None]
    })
    df4 = comp.upsert_ratio_column(df3)
    assert "Put/Call Yield Ratio" in df4.columns
    assert df4["Put/Call Yield Ratio"].iloc[0] == 2
    assert pd.isna(df4["Put/Call Yield Ratio"].iloc[1])
    out, _ = capfd.readouterr()
    assert 'Column "Put/Call Yield Ratio" already exists. Updating values.' in out

    # Case 3: Error handling (simulate missing columns)
    df5 = pd.DataFrame({"Other Col": [1, 2]})
    df6 = comp.upsert_ratio_column(df5)
    out, _ = capfd.readouterr()
    assert "Error in upsert_ratio_column:" in out