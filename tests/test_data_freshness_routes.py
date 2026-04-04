from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import BackgroundTasks
import pandas as pd

from app.api import routes
from app.models import User


def test_evaluate_stock_data_freshness_marks_recent_record_fresh():
    stock = {"_last_persisted_at": datetime.now(timezone.utc).isoformat()}
    freshness = routes._evaluate_stock_data_freshness(stock, tier="mixed")  # pylint: disable=protected-access
    assert freshness["is_stale"] is False
    assert freshness["refresh_queued"] is False
    assert freshness["last_updated"] is not None


def test_get_ticker_analysis_marks_stale_and_queues_refresh_task():
    stale_iso = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)

    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AAPL",
            "Current Price": 150.0,
            "Company Name": "Apple Inc.",
            "_last_persisted_at": stale_iso,
        }
        payload = routes.get_ticker_analysis("AAPL", bt, admin)

    assert payload["found"] is True
    assert payload["is_stale"] is True
    assert payload["refresh_queued"] is True
    assert len(bt.tasks) == 1
    assert bt.tasks[0].func is routes.run_stock_live_comparison
    assert bt.tasks[0].args == (["AAPL"], "sync")


def test_get_ticker_signals_prefers_persisted_db_signals_without_yfinance():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.api.routes.yf.download") as mock_download:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "SPY",
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
            "signals": {
                "kalman": {"signal": "Bullish"},
                "markov": {"current_state": "UP"},
                "advice": {"decision": "HOLD"},
            },
        }
        payload = routes.get_ticker_signals("SPY", bt, admin)

    assert payload["ticker"] == "SPY"
    assert payload["kalman"]["signal"] == "Bullish"
    assert payload["markov"]["current_state"] == "UP"
    assert payload["is_stale"] is False
    mock_download.assert_not_called()


def test_get_ticker_signals_falls_back_to_yfinance_when_db_signals_absent():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.api.routes.SignalService") as mock_service_cls, patch(
        "app.api.routes.yf.download"
    ) as mock_download:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        mock_download.return_value = pd.DataFrame({"Close": [100, 101]})
        service = mock_service_cls.return_value
        service.get_kalman_signal.return_value = {"signal": "Bullish"}
        service.get_markov_probabilities.return_value = {"current_state": "UP"}
        service.get_roll_vs_hold_advice.return_value = {"decision": "HOLD"}

        payload = routes.get_ticker_signals("SPY", bt, admin)

    assert payload["ticker"] == "SPY"
    assert payload["kalman"]["signal"] == "Bullish"
    assert payload["data_source"] == "yfinance_live"
    assert payload["is_stale"] is True
    assert payload["stale_reason"] == "db_record_missing"
