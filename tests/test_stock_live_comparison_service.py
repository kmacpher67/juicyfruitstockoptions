from app.services import stock_live_comparison as svc


class DummyComparison:
    def __init__(self, tickers):
        self.tickers = tickers
        self.filename = "report-results/AI_Stock_Live_Comparison_20260402_052900.xlsx"
        self.run_calls = []

    @staticmethod
    def get_default_tickers():
        return ["AAPL", "MSFT"]

    def run(self, force_new_file=False, allow_create_if_missing=True):
        self.run_calls.append(
            {
                "force_new_file": force_new_file,
                "allow_create_if_missing": allow_create_if_missing,
            }
        )


def test_service_manual_trigger_creates_new_file(monkeypatch):
    created = {}

    def fake_ctor(tickers):
        created["comp"] = DummyComparison(tickers)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    result = svc.run_stock_live_comparison(["AAPL"], trigger="manual")

    assert result["status"] == "success"
    assert created["comp"].run_calls == [
        {"force_new_file": True, "allow_create_if_missing": True}
    ]


def test_service_sync_trigger_reuses_existing_without_new_file(monkeypatch):
    created = {}

    def fake_ctor(tickers):
        created["comp"] = DummyComparison(tickers)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    result = svc.run_stock_live_comparison(["AAPL"], trigger="sync")

    assert result["status"] == "success"
    assert created["comp"].run_calls == [
        {"force_new_file": False, "allow_create_if_missing": False}
    ]

