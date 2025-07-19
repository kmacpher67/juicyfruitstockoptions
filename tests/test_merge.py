import pandas as pd
from stock_live_comparison import StockLiveComparison

def test_merge_with_existing():
    comp = StockLiveComparison(['AAA','BBB'])
    comp.records = [
        {'Ticker': 'AAA', 'Current Price': 100, 'Annual Yield Put Prem': 1, 'Annual Yield Call Prem': 2}
    ]
    existing = pd.DataFrame([
        {'Ticker': 'AAA', 'Current Price': 90, 'Annual Yield Put Prem': 0, 'Annual Yield Call Prem': 0},
        {'Ticker': 'BBB', 'Current Price': 80, 'Annual Yield Put Prem': 0, 'Annual Yield Call Prem': 0},
    ])
    merged = comp.merge_with_existing(existing, ['AAA'])
    assert len(merged) == 2
    assert merged[merged['Ticker']=='AAA']['Current Price'].iloc[0] == 100
    assert merged[merged['Ticker']=='BBB']['Current Price'].iloc[0] == 80
