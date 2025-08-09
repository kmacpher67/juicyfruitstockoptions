import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from stock_live_comparison import StockLiveComparison

class DummyOptionChain:
    def __init__(self, calls_df, puts_df, dates):
        self._calls_df = calls_df
        self._puts_df = puts_df
        self.options = dates
    def option_chain(self, exp):
        class OC:
            def __init__(self, calls, puts):
                self.calls = calls
                self.puts = puts
        return OC(self._calls_df, self._puts_df)

def test_closest_expiration():
    today = pd.Timestamp.now()
    dates = [
        (today + pd.Timedelta(days=5)).strftime('%Y-%m-%d'),
        (today + pd.Timedelta(days=14)).strftime('%Y-%m-%d'),
        (today + pd.Timedelta(days=40)).strftime('%Y-%m-%d'),
    ]
    result = StockLiveComparison.closest_expiration(dates, 10)
    assert result == dates[1]

def test_get_otm_call_and_put_yields(monkeypatch):
    def fake_closest(option_dates, td):
        return '2030-01-01'
    monkeypatch.setattr(StockLiveComparison, 'closest_expiration', staticmethod(fake_closest))
    calls = pd.DataFrame({'strike':[106,110], 'lastPrice':[1.0, 2.0]})
    puts = pd.DataFrame({'strike':[94,90], 'lastPrice':[1.5, 2.0]})
    chain = DummyOptionChain(calls, puts, ['2030-01-01'])
    comp = StockLiveComparison(['AAA'])
    call_yield, strike = comp.get_otm_call_yield(chain, 100, 90)
    put_price = comp.get_otm_put_price(chain, 100, 90)
    assert call_yield == 1.0
    assert strike == 106
    assert put_price == 2.0

def test_sort_dataframe_for_excel():
    import pandas as pd
    from stock_live_comparison import StockLiveComparison
    comp = StockLiveComparison(["AAPL", "MSFT"])
    df = pd.DataFrame({
        "Ticker": ["MSFT", "AAPL", "MSFT"],
        "Last Update": ["2024-07-22 10:00:00", "2024-07-23 09:00:00", "2024-07-23 11:00:00"],
        "Other": [1, 2, 3]
    })
    sorted_df = comp.sort_dataframe_for_excel(df)
    # Check that the first row is the newest update
    assert sorted_df.iloc[0]["Last Update"] == "2024-07-23 11:00:00"
    # Check that within same Last Update, Ticker is sorted ascending
    assert list(sorted_df["Ticker"]) == ["MSFT", "AAPL", "MSFT"]
