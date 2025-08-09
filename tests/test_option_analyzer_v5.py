import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

import option_analyzer_v5 as mod


class DummyTicker:
    def __init__(self):
        self.expiry = (pd.Timestamp.today() + pd.Timedelta(days=30)).strftime("%Y-%m-%d")

    def history(self, period="1d"):
        return pd.DataFrame({"Close": [100]})

    @property
    def options(self):
        return [self.expiry]

    def option_chain(self, expiry):
        calls = pd.DataFrame(
            {
                "strike": [105],
                "lastPrice": [2.0],
                "bid": [1.9],
                "ask": [2.1],
                "volume": [100],
                "openInterest": [10],
            }
        )
        class OC:
            pass
        oc = OC()
        oc.calls = calls
        return oc


def test_analyze_options(monkeypatch):
    monkeypatch.setattr(mod, "yf", type("YF", (), {"Ticker": lambda symbol: DummyTicker()}))
    df = mod.analyze_options(
        ticker_symbol="AAA",
        min_volume=50,
        max_expirations=1,
        min_annual_tv_pct=10,
        max_otm_pct=10,
    )
    assert list(df["Strike"]) == [105]
