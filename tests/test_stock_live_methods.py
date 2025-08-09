import pandas as pd
import openpyxl
import pytest
from stock_live_comparison import StockLiveComparison


class DummyChain:
    def option_chain(self, exp):
        class OC:
            def __init__(self):
                self.calls = pd.DataFrame()
                self.puts = pd.DataFrame()
        return OC()


def test_fetch_data_empty_tickers():
    comp = StockLiveComparison([])
    assert comp.fetch_data([]) == []


def test_fetch_data_api_failure(monkeypatch):
    import stock_live_comparison as slc

    def fake_download(*args, **kwargs):
        return {}

    class BadTicker:
        @property
        def info(self):
            raise ValueError("boom")

    class DummyTickers:
        def __init__(self):
            self.tickers = {"AAA": BadTicker()}

    monkeypatch.setattr(slc.yf, "download", fake_download)
    monkeypatch.setattr(slc.yf, "Tickers", lambda symbols: DummyTickers())
    monkeypatch.setattr(slc.time, "sleep", lambda x: None)

    comp = StockLiveComparison(["AAA"])
    records = comp.fetch_data(["AAA"])
    assert len(records) == 1
    assert records[0]["Ticker"] == "AAA"
    assert records[0]["Error"] == "boom"


def test_fetch_ticker_record(monkeypatch):
    comp = StockLiveComparison(["AAA"])

    def fake_call(chain, price, days, otm_pct=6):
        mapping = {90: (1, None), 180: (2, 105), 365: (3, None)}
        return mapping[days]

    def fake_put(chain, price, days, otm_pct=6):
        return 5

    comp.get_otm_call_yield = fake_call
    comp.get_otm_put_price = fake_put

    info = {
        "regularMarketPrice": 100,
        "marketCap": 2e12,
        "trailingPE": 15,
        "dividendYield": 0.01,
        "targetMeanPrice": 120,
        "exDividendDate": 1710000000,
    }
    hist = pd.DataFrame({"Close": [90, 100]})
    record = comp.fetch_ticker_record("AAA", info, hist, DummyChain())
    assert record["Ticker"] == "AAA"
    assert record["1D % Change"] == "11.11%"
    assert record["YoY Price %"] == "11.1%"
    assert record["3-mo Call Yield"] == 1
    assert record["6-mo Call Yield"] == 2
    assert record["Example 6-mo Strike"] == 105
    assert record["1-yr Call Yield"] == 3
    assert record["1-yr 6% OTM PUT Price"] == 5
    assert record["Annual Yield Put Prem"] == 5
    assert record["Annual Yield Call Prem"] == 3


def test_add_ratio_column():
    comp = StockLiveComparison(["AAA"])
    df = pd.DataFrame([
        {"Annual Yield Put Prem": 5, "Annual Yield Call Prem": 10},
        {"Annual Yield Put Prem": None, "Annual Yield Call Prem": 5},
    ])
    df, put_col, call_col = comp.add_ratio_column(df)
    assert "Put/Call Yield Ratio" in df.columns
    assert df.iloc[0]["Put/Call Yield Ratio"] == 0.5
    assert pd.isna(df.iloc[1]["Put/Call Yield Ratio"])
    assert put_col == 1 and call_col == 2


def test_upsert_ratio_column():
    comp = StockLiveComparison(["AAA"])
    df = pd.DataFrame({"Annual Yield Put Prem": [5], "Annual Yield Call Prem": [10]})
    df = comp.upsert_ratio_column(df)
    assert df.iloc[0]["Put/Call Yield Ratio"] == 0.5
    df["Annual Yield Call Prem"] = [5]
    df = comp.upsert_ratio_column(df)
    assert df.iloc[0]["Put/Call Yield Ratio"] == 1.0


def test_save_to_excel(tmp_path):
    comp = StockLiveComparison(["AAA"])
    comp.filename = str(tmp_path / "out.xlsx")
    df = pd.DataFrame({
        "Ticker": ["AAA"],
        "Annual Yield Put Prem": [5],
        "Annual Yield Call Prem": [10],
    })
    df, put_col, call_col = comp.add_ratio_column(df)
    comp.save_to_excel(df, put_col, call_col)
    wb = openpyxl.load_workbook(comp.filename)
    ws = wb.active
    assert ws.freeze_panes == "A2"
    ratio_cell = ws.cell(row=2, column=call_col + 1)
    put_letter = openpyxl.utils.get_column_letter(put_col)
    call_letter = openpyxl.utils.get_column_letter(call_col)
    assert ratio_cell.value == f"=IFERROR({put_letter}2/{call_letter}2,\"\")"
    assert ws["A1"].font.bold


def test_run(monkeypatch):
    sample_record = {
        "Ticker": "AAA",
        "Annual Yield Put Prem": 5,
        "Annual Yield Call Prem": 10,
    }

    monkeypatch.setattr(StockLiveComparison, "get_latest_spreadsheet", staticmethod(lambda base_name="AI_Stock_Live_Comparison_": (None, None)))

    def fake_fetch(self, tickers):
        return [sample_record]

    monkeypatch.setattr(StockLiveComparison, "fetch_data", fake_fetch)

    saved = {}

    def fake_save(self, df, put_col, call_col):
        saved["df"] = df.copy()
        saved["put_col"] = put_col
        saved["call_col"] = call_col

    monkeypatch.setattr(StockLiveComparison, "save_to_excel", fake_save)

    comp = StockLiveComparison(["AAA"])
    comp.run()
    df = saved["df"]
    assert "Put/Call Yield Ratio" in df.columns
    assert df.iloc[0]["Put/Call Yield Ratio"] == 0.5
    assert saved["put_col"] == 2 and saved["call_col"] == 3
