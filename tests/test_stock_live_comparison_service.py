from app.services import stock_live_comparison as svc
from unittest.mock import patch


class DummyComparison:
    def __init__(self, tickers, **kwargs):
        self.tickers = tickers
        self.kwargs = kwargs
        self.filename = "report-results/AI_Stock_Live_Comparison_20260402_052900.xlsx"
        self.run_calls = []
        self.output_dir = "report-results"
        self.min_viable_report_bytes = 10240

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
        requested = len(self.tickers or [])
        return {
            "requested_tickers_count": requested,
            "stale_candidate_count": requested,
            "stale_hit_ratio": 1.0 if requested else 0.0,
            "fetched_records_count": requested,
            "successful_fetch_count": requested,
            "failed_fetch_count": 0,
            "failed_tickers": [],
            "rows_written": requested,
        }

    def get_latest_viable_spreadsheet(self, directory, min_bytes=10 * 1024):
        return self.filename, None


def test_service_manual_trigger_creates_new_file(monkeypatch):
    created = {}

    def fake_ctor(tickers, **kwargs):
        created["comp"] = DummyComparison(tickers, **kwargs)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        result = svc.run_stock_live_comparison(["AAPL"], trigger="manual")

    assert result["status"] == "success"
    assert created["comp"].run_calls == [
        {"force_new_file": True, "allow_create_if_missing": True}
    ]
    mock_db.stock_ingest_runs.insert_one.assert_called_once()
    payload = mock_db.stock_ingest_runs.insert_one.call_args.args[0]
    assert payload["source_used"] == "yfinance_live"
    assert payload["rows_updated"] == 1
    assert payload["stale_hit_ratio"] == 1.0
    assert payload["failure_count"] == 0
    assert payload["failures"] == []


def test_service_sync_trigger_reuses_existing_without_new_file(monkeypatch):
    created = {}

    def fake_ctor(tickers, **kwargs):
        created["comp"] = DummyComparison(tickers, **kwargs)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        result = svc.run_stock_live_comparison(["AAPL"], trigger="sync")

    assert result["status"] == "success"
    assert created["comp"].run_calls == [
        {"force_new_file": False, "allow_create_if_missing": False}
    ]
    mock_db.stock_ingest_runs.insert_one.assert_called_once()


def test_service_sync_trigger_skips_when_no_viable_existing_report(monkeypatch):
    created = {}

    class DummyNoViable(DummyComparison):
        def get_latest_viable_spreadsheet(self, directory, min_bytes=10 * 1024):
            return None, None

    def fake_ctor(tickers, **kwargs):
        created["comp"] = DummyNoViable(tickers, **kwargs)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        result = svc.run_stock_live_comparison(["AAPL"], trigger="sync")

    assert result["status"] == "skipped"
    assert result["reason"] == "no_viable_existing_report_for_sync"
    assert created["comp"].run_calls == []
    mock_db.stock_ingest_runs.insert_one.assert_called_once()
    payload = mock_db.stock_ingest_runs.insert_one.call_args.args[0]
    assert payload["source_used"] == "none"
    assert payload["rows_updated"] == 0
    assert payload["failure_count"] == 0
    assert payload["failures"] == []


def test_service_error_persists_telemetry(monkeypatch):
    class DummyError(DummyComparison):
        def run(self, force_new_file=False, allow_create_if_missing=True):
            raise RuntimeError("boom")

    monkeypatch.setattr(svc, "StockLiveComparison", lambda tickers: DummyError(tickers))
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        result = svc.run_stock_live_comparison(["AAPL"], trigger="manual")

    assert result["status"] == "error"
    mock_db.stock_ingest_runs.insert_one.assert_called_once()
    payload = mock_db.stock_ingest_runs.insert_one.call_args.args[0]
    assert payload["source_used"] == "yfinance_live"
    assert payload["rows_updated"] == 0
    assert payload["failure_count"] == 0


def test_service_uses_stock_analysis_http_settings_from_system_config(monkeypatch):
    created = {}

    def fake_ctor(tickers, **kwargs):
        created["comp"] = DummyComparison(tickers, **kwargs)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {
            "_id": "stock_analysis_http_config",
            "download_batch_size": 3,
            "batch_pause_sec": 1.25,
            "request_throttle_interval_sec": 0.5,
        }
        result = svc.run_stock_live_comparison(["AAPL"], trigger="manual")

    assert result["status"] == "success"
    assert created["comp"].kwargs["download_batch_size"] == 3
    assert created["comp"].kwargs["batch_pause_sec"] == 1.25
    assert created["comp"].kwargs["min_request_interval_sec"] == 0.5
    mock_db.stock_ingest_runs.insert_one.assert_called_once()


def test_service_coerces_invalid_stock_analysis_http_settings_to_safe_defaults(monkeypatch):
    created = {}

    def fake_ctor(tickers, **kwargs):
        created["comp"] = DummyComparison(tickers, **kwargs)
        return created["comp"]

    monkeypatch.setattr(svc, "StockLiveComparison", fake_ctor)
    with patch("app.services.stock_live_comparison.MongoClient") as mock_mongo:
        mock_db = mock_mongo.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {
            "_id": "stock_analysis_http_config",
            "download_batch_size": "bad",
            "batch_pause_sec": -7,
            "request_throttle_interval_sec": None,
        }
        result = svc.run_stock_live_comparison(["AAPL"], trigger="manual")

    assert result["status"] == "success"
    assert created["comp"].kwargs["download_batch_size"] == 6
    assert created["comp"].kwargs["batch_pause_sec"] == 0.0
    assert created["comp"].kwargs["min_request_interval_sec"] == 1.5
