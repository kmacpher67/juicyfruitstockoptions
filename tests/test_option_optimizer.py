import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

import option_optimizer as mod


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
                "strike": [105, 110],
                "lastPrice": [2.0, 1.0],
                "bid": [1.9, 0.9],
                "ask": [2.1, 1.1],
                "volume": [100, 100],
                "openInterest": [10, 10],
            }
        )
        class OC:
            pass
        oc = OC()
        oc.calls = calls
        return oc


def test_optimize_options(monkeypatch):
    monkeypatch.setattr(mod, "yf", type("YF", (), {"Ticker": lambda symbol: DummyTicker()}))
    df = mod.optimize_options(
        ticker_symbol="AAA",
        min_volume=50,
        max_expirations=1,
        min_annual_tv_pct=0,
        max_otm_pct=10,
        min_days=1,
        max_results=1,
    )
    assert len(df) == 1
    assert df.iloc[0]["Strike"] == 105
