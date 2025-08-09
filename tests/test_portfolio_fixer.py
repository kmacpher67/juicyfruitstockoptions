import importlib.util
import pathlib
import pandas as pd

def load_module():
    path = pathlib.Path(__file__).resolve().parents[1] / "portfolio-fixer.py"
    spec = importlib.util.spec_from_file_location("portfolio_fixer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

pf = load_module()


def test_calculate_coverage():
    option_positions = pd.DataFrame(
        {
            "Financial Instrument Description": ["AAPL Jan24C150"],
            "Position": [-1],
        }
    )
    total, free = pf.calculate_coverage(200, option_positions)
    assert total == 100
    assert free == 100


def test_evaluate_stock_position_sell_calls(monkeypatch):
    def fake_price(ticker):
        return 150

    def fake_analyze(**kwargs):
        return pd.DataFrame(
            [
                {
                    "Expiration": "2024-01-19",
                    "Strike": 155,
                    "Last": 2.0,
                    "Volume": 100,
                    "Ann.TV%": 12.0,
                    "Dist.%": 3.0,
                }
            ]
        )

    monkeypatch.setattr(pf, "get_current_price", fake_price)
    monkeypatch.setattr(pf, "analyze_option_chain", fake_analyze)

    stock = pd.Series(
        {
            "Financial Instrument Description": "AAPL",
            "Position": 100,
        }
    )
    option_positions = pd.DataFrame(
        columns=["Financial Instrument Description", "Position"]
    )
    recs = pf.evaluate_stock_position(stock, option_positions, "2024-01-01 00:00:00")
    assert recs[0]["Recommendation"] == "Sell Covered Call"
    assert recs[0]["Ticker"] == "AAPL"


def test_evaluate_stock_position_consider_rolling(monkeypatch):
    def fake_price(ticker):
        return 150

    def fake_analyze(**kwargs):
        return pd.DataFrame(
            [
                {
                    "Expiration": "2024-02-16",
                    "Strike": 160,
                    "Last": 1.5,
                    "Volume": 200,
                    "Ann.TV%": 15.0,
                    "Dist.%": 5.0,
                }
            ]
        )

    monkeypatch.setattr(pf, "get_current_price", fake_price)
    monkeypatch.setattr(pf, "analyze_option_chain", fake_analyze)

    stock = pd.Series(
        {
            "Financial Instrument Description": "AAPL",
            "Position": 100,
        }
    )
    option_positions = pd.DataFrame(
        {
            "Financial Instrument Description": ["AAPL 2024C150"],
            "Position": [-1],
            "Expiration": ["2024-01-19"],
            "Strike": [150],
            "Market Price": [3.0],
            "Volume": [50],
            "Ann.TV%": [10.0],
            "Dist.%": [1.0],
        }
    )
    recs = pf.evaluate_stock_position(stock, option_positions, "2024-01-01 00:00:00")
    assert recs[0]["Recommendation"] == "Consider Rolling to Better Option"
