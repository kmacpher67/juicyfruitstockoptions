import json
from pathlib import Path
from stock_live_comparison import StockLiveComparison


def test_update_category_rules(tmp_path):
    p = tmp_path / "category_rules.json"
    # Apply multiple similar descriptions mapping to 'Gas'
    StockLiveComparison.update_category_rules(p, "BP 8296725CLARIDON B EAST CLARIDON OH", "Gas", max_terms=1)
    StockLiveComparison.update_category_rules(p, "BP 8296725CLARIDON BP EAST CLARIDONOH", "Gas", max_terms=1)
    StockLiveComparison.update_category_rules(p, "BP 9709726CIRCLE K WARREN OH", "Gas", max_terms=1)
    StockLiveComparison.update_category_rules(p, "CIRCLE K WARREN OH", "Gas", max_terms=1)
    # Another merchant
    StockLiveComparison.update_category_rules(p, "WALMART STORE #1234", "Retail", max_terms=1)

    data = json.loads(p.read_text())
    assert data.get("BP") == "Gas"
    assert data.get("CIRCLE") == "Gas"
    assert data.get("WALMART") == "Retail"
