import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

import covered_call_analysis as mod


def test_analyze_covered_calls(monkeypatch):
    csv_data = (
        "Open Positions,Data,Stocks,USD,AAA,ACC1,200\n"
        "Open Positions,Data,Equity and Index Options,USD,AAA 20250119 C100,ACC1,-1\n"
    )
    monkeypatch.setattr("builtins.open", lambda fp, newline='': io.StringIO(csv_data))
    df = mod.analyze_covered_calls("dummy.csv")
    assert df.iloc[0]["Calls Available to Sell"] == 1
    assert not df.iloc[0]["Naked Short?"]
