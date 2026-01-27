import pandas as pd
from datetime import datetime, timedelta
from stock_live_comparison import StockLiveComparison

## Component Test cases for StockLiveComparison class
## Test checks if output files are created correctly and contain expected data.
def test_run_creates_spreadsheet(tmp_path):
    tickers = ["AAPL", "MSFT"]
    comp = StockLiveComparison(tickers)
    # Override output_dir for test to avoid polluting report-results
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
        {
            "Ticker": "AAPL", "Last Update": recent_time, 
            "MA_30": 100, "MA_60": 100, "MA_120": 100, "MA_200": 100,
            "EMA_20": 100, "HMA_20": 100, "TSMOM_60": 0.05,
            "_PutExpDate_365": "2024-01-01"
        },
        {
            "Ticker": "MSFT", "Last Update": old_time, 
            "MA_30": 100, "MA_60": 100, "MA_120": 100, "MA_200": 100,
             "EMA_20": 100, "HMA_20": 100, "TSMOM_60": 0.05,
            "_PutExpDate_365": "2024-01-01"
        },
        {
            "Ticker": "GOOG", "Last Update": None, 
            "MA_30": 100, "MA_60": 100, "MA_120": 100, "MA_200": 100,
             "EMA_20": 100, "HMA_20": 100, "TSMOM_60": 0.05,
            "_PutExpDate_365": "2024-01-01"
        },
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
        "Call/Put Skew": [0.5, None]  # Already exists
    })
    # Should not crash, should print error, and should return df unchanged
    df2, put_col, call_col = comp.add_ratio_column(df)
    assert "Call/Put Skew" in df2.columns
    # The values should be updated for valid rows
    assert df2["Call/Put Skew"].iloc[0] == 0.5
    assert df2["Call/Put Skew"].iloc[1] == 0.0 # 0 / 20 = 0.0

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
    assert "Call/Put Skew" in df2.columns
    assert df2["Call/Put Skew"].iloc[0] == 0.5 # 5 / 10
    assert df2["Call/Put Skew"].iloc[1] == 0.0
    # out, err = capfd.readouterr()
    # assert 'Column "Call/Put Skew" inserted.' in (out + err)

    # Case 2: Column already exists
    df3 = pd.DataFrame({
        "Annual Yield Put Prem": [10, 20],
        "Annual Yield Call Prem": [5, 0],
        "Call/Put Skew": [None, None]
    })
    df4 = comp.upsert_ratio_column(df3)
    assert "Call/Put Skew" in df4.columns
    assert df4["Call/Put Skew"].iloc[0] == 0.5
    assert df4["Call/Put Skew"].iloc[1] == 0.0
    # out, err = capfd.readouterr()
    # assert 'Column "Call/Put Skew" already exists. Updating values.' in (out + err)

    # Case 3: Error handling (simulate missing columns)
    df5 = pd.DataFrame({"Other Col": [1, 2]})
    df6 = comp.upsert_ratio_column(df5)
    df6 = comp.upsert_ratio_column(df5)
    # out, err = capfd.readouterr()
    # assert "Error in upsert_ratio_column:" in (out + err)

def test_upsert_to_mongo_idempotent(monkeypatch):
    import pandas as pd
    from stock_live_comparison import StockLiveComparison
    from Ai_Stock_Database import AiStockDatabase

    # Use a test DB
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_stocklive")
    comp = StockLiveComparison(["AAPL"])
    db = AiStockDatabase(db_name="test_stocklive", collection_name="test_stock_data")
    db.collection.delete_many({})  # Clean up before test

    df = pd.DataFrame([
        {"Ticker": "AAPL", "Last Update": "2024-07-23 10:00:00", "Price": 100},
        {"Ticker": "AAPL", "Last Update": "2024-07-23 10:00:00", "Price": 100}
    ])
    comp.upsert_to_mongo(df)
    # Should only be one record for AAPL at that Last Update
    assert db.collection.count_documents({"Ticker": "AAPL", "Last Update": "2024-07-23 10:00:00"}) == 1

def test_unique_tickers():
    from stock_live_comparison import StockLiveComparison
    tickers = ["AAPL", "MSFT", "AAPL", "GOOG", "MSFT", "TSLA"]
    result = StockLiveComparison.unique_tickers(tickers)
    assert result == ["AAPL", "MSFT", "GOOG", "TSLA"]

def test_get_missing_or_outdated_includes_nan_ma():
    from stock_live_comparison import StockLiveComparison
    comp = StockLiveComparison(["AAPL"])
    now = datetime.now()
    recent_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Simulate DataFrame where valid time exists but MAs are missing (NaN)
    df_existing = pd.DataFrame([
        {
            "Ticker": "AAPL", 
            "Last Update": recent_time,
            "MA_30": None,   # Missing
            "MA_60": 150.0,  # Present
            "MA_120": float("nan"), # Missing
            "MA_200": 140.0
        }
    ])
    
    missing_or_old = comp.get_missing_or_outdated_tickers(df_existing)
    # Should automatically include AAPL because MA_30 and MA_120 are missing/NaN
    assert "AAPL" in missing_or_old

def test_get_missing_or_outdated_detects_legacy_strings():
    from stock_live_comparison import StockLiveComparison
    comp = StockLiveComparison(["AAPL"])
    now = datetime.now()
    recent_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Simulate DataFrame with recent update but legacy "red"/"green" strings
    df_existing = pd.DataFrame([
        {
            "Ticker": "AAPL", 
            "Last Update": recent_time,
            "MA_30": 100, 
            "MA_60": 100, 
            "MA_120": 100, 
            "MA_200": 100,
            "MA_30_highlight": "red",     # Legacy string
            "MA_60_highlight": "green",   # Legacy string
            "MA_120_highlight": 0.05,     # Correct format
            "MA_200_highlight": 0.05
        }
    ])
    
    missing_or_old = comp.get_missing_or_outdated_tickers(df_existing)
    # Should include AAPL because it has "red"/"green" strings
    assert "AAPL" in missing_or_old