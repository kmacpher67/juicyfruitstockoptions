import pytest
from app.services.options_analysis import OptionsAnalyzer

# Mock Data
# 1. Fully Covered: 100 Shares, -1 Call
# 2. Uncovered: 200 Shares, -1 Call (100 shares free)
# 3. Naked: 0 Shares, -1 Call
# 4. Profit: -1 Call, Cost -100, Mkt -10 (90% profit)

MOCK_HOLDINGS = [
    # AAPL: Fully Covered
    {"account_id": "U1", "symbol": "AAPL", "sec_type": "STK", "quantity": 100, "underlying": "AAPL"},
    {"account_id": "U1", "symbol": "AAPL 250117C00200000", "sec_type": "OPT", "quantity": -1, "underlying": "AAPL", "multiplier": 100},

    # TSLA: Uncovered (Partial)
    {"account_id": "U1", "symbol": "TSLA", "sec_type": "STK", "quantity": 200, "underlying": "TSLA"},
    {"account_id": "U1", "symbol": "TSLA 250117C00200000", "sec_type": "OPT", "quantity": -1, "underlying": "TSLA", "multiplier": 100},

    # NVDA: Naked Call
    {"account_id": "U1", "symbol": "NVDA 250117C00200000", "sec_type": "OPT", "quantity": -1, "underlying": "NVDA", "multiplier": 100},

    # AMD: Profit Opportunity (Short Put or Call)
    # Cost Basis -500 (Credit), Market Value -50 (Buyback Cost). PnL +450. (90%)
    {"account_id": "U1", "symbol": "AMD 250117P00100000", "sec_type": "OPT", "quantity": -5, "underlying": "AMD", "multiplier": 100, 
     "cost_basis": -500.0, "market_value": -50.0, "unrealized_pnl": 450.0}
]

def test_analyze_coverage():
    analyzer = OptionsAnalyzer(MOCK_HOLDINGS)
    alerts = analyzer.analyze_coverage()
    
    # Expect TSLA to be in alerts (Uncovered)
    tsla = next((a for a in alerts if a['symbol'] == 'TSLA'), None)
    assert tsla is not None
    assert tsla['type'] == 'UNCOVERED_SHARES'
    assert tsla['shares_owned'] == 200
    assert tsla['shares_covered'] == 100
    assert tsla['shares_free'] == 100

def test_analyze_naked():
    analyzer = OptionsAnalyzer(MOCK_HOLDINGS)
    alerts = analyzer.analyze_naked()
    
    # Expect NVDA (Naked)
    nvda = next((a for a in alerts if a['symbol'] == 'NVDA'), None)
    assert nvda is not None
    assert nvda['type'] == 'NAKED_OPTION'
    assert nvda['short_contracts'] == 1
    
    # AAPL should NOT be naked
    aapl = next((a for a in alerts if a['symbol'] == 'AAPL'), None)
    assert aapl is None

def test_analyze_profit():
    analyzer = OptionsAnalyzer(MOCK_HOLDINGS)
    # Threshold 50%
    alerts = analyzer.analyze_profit(threshold_pct=0.50)
    
    # Expect AMD
    amd = next((a for a in alerts if 'AMD' in a['symbol']), None)
    assert amd is not None
    assert amd['type'] == 'PROFIT_TAKE'
    assert amd['profit_pct'] == 0.90 # 450 / 500
