import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

import option_time_value as mod


class DummyTicker:
    def __init__(self):
        self.expiry = (pd.Timestamp.today() + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        self.info = {"regularMarketPrice": 100}

    @property
    def options(self):
        return [self.expiry]

    def option_chain(self, date):
        calls = pd.DataFrame(
            {
                "strike": [105, 110],
                "lastPrice": [2.0, 1.0],
                "volume": [100, 100],
                "openInterest": [10, 10],
            }
        )
        class OC:
            pass
        oc = OC()
        oc.calls = calls
        return oc


def test_calculate_time_value():
    row = pd.Series({"stockPrice": 100, "strike": 105, "lastPrice": 2.5})
    assert mod.calculate_time_value(row) == 2.5


def test_analyze_options(monkeypatch):
    monkeypatch.setattr(mod, "yf", type("YF", (), {"Ticker": lambda symbol: DummyTicker()}))
    df = mod.analyze_options(["AAA"], min_time_value=1.5)
    assert list(df["strike"]) == [105]
    assert list(df["ticker"]) == ["AAA"]
