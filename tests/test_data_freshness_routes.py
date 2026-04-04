from datetime import datetime, timedelta, timezone
import math
from unittest.mock import patch

from fastapi import BackgroundTasks
import pandas as pd

from app.api import routes
from app.models import User
from app.services.data_refresh_queue import get_data_refresh_queue


def setup_function():
    get_data_refresh_queue().clear()


def test_evaluate_stock_data_freshness_marks_recent_record_fresh():
    stock = {"_last_persisted_at": datetime.now(timezone.utc).isoformat()}
    freshness = routes._evaluate_stock_data_freshness(stock, tier="mixed")  # pylint: disable=protected-access
    assert freshness["is_stale"] is False
    assert freshness["refresh_queued"] is False
    assert freshness["last_updated"] is not None


def test_evaluate_stock_data_freshness_respects_system_config_threshold_override():
    stock = {"_last_persisted_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()}
    fake_db = type("DB", (), {})()
    fake_db.system_config = type("Collection", (), {})()
    fake_db.system_config.find_one = lambda query: {"price_open_min": 60}

    with patch("app.api.routes._is_us_equity_market_session", return_value=True):
        freshness = routes._evaluate_stock_data_freshness(stock, tier="price", db=fake_db)  # pylint: disable=protected-access
    assert freshness["is_stale"] is False


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
    mock_db.stock_data.update_one.assert_called_once()


def test_queue_stock_refresh_if_stale_respects_cooldown():
    bt = BackgroundTasks()
    freshness = {
        "is_stale": True,
        "refresh_queued": False,
        "stale_reason": "older_than_30m",
    }
    symbol = "AAPL"
    now_utc = datetime.now(timezone.utc)

    queue = get_data_refresh_queue()
    queue.should_enqueue(symbol, now_utc=now_utc)
    routes._queue_stock_refresh_if_stale(bt, symbol, freshness)  # pylint: disable=protected-access

    assert len(bt.tasks) == 0
    assert freshness["refresh_queued"] is False
    assert freshness["stale_reason"] == "older_than_30m"


def test_get_portfolio_optimizer_include_meta_returns_freshness_payload():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "TSLA",
            "Current Price": 100.0,
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.ibkr_holdings.find.return_value = []
        payload = routes.get_portfolio_optimizer("TSLA", bt, include_meta=True, current_user=admin)

    assert payload["symbol"] == "TSLA"
    assert payload["is_stale"] is False
    assert isinstance(payload["suggestions"], list)
    assert payload["suggestions"][0]["strategy"] == "Covered Call"


def test_get_portfolio_optimizer_stale_record_queues_refresh():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "TSLA",
            "Current Price": 100.0,
            "_last_persisted_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        }
        mock_db.ibkr_holdings.find.return_value = []
        payload = routes.get_portfolio_optimizer("TSLA", bt, include_meta=True, current_user=admin)

    assert payload["is_stale"] is True
    assert payload["refresh_queued"] is True
    assert len(bt.tasks) == 1


def test_get_ticker_price_history_returns_db_rows_with_freshness():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AAPL",
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_cursor = mock_db.instrument_price_history.find.return_value
        mock_cursor.sort.return_value.limit.return_value = [
            {"instrument_key": "AAPL", "timestamp": "2026-04-04 10:01:00", "price": 201.0},
            {"instrument_key": "AAPL", "timestamp": "2026-04-04 10:00:00", "price": 200.0},
        ]

        payload = routes.get_ticker_price_history("AAPL", admin, limit=100)

    assert payload["symbol"] == "AAPL"
    assert payload["count"] == 2
    assert payload["history"][0]["timestamp"] == "2026-04-04 10:00:00"
    assert payload["is_stale"] is False


def test_get_ticker_price_history_clamps_limit():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {"Ticker": "AAPL"}
        mock_cursor = mock_db.instrument_price_history.find.return_value
        mock_cursor.sort.return_value.limit.return_value = []

        routes.get_ticker_price_history("AAPL", admin, limit=999999)

    mock_cursor.sort.return_value.limit.assert_called_once_with(5000)


def test_analyze_ticker_smart_rolls_include_meta_returns_freshness_payload():
    admin = User(username="u", role="admin", disabled=False)
    bt = BackgroundTasks()
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.services.roll_service.RollService") as mock_roll_cls:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "snap1"}
        mock_db.ibkr_holdings.find.return_value = [{"symbol": "AMD", "secType": "OPT"}]
        mock_roll_cls.return_value.analyze_portfolio_rolls.return_value = [
            {"rolls": [{"score": 80, "strike": 200}, {"score": 70, "strike": 190}]}
        ]

        payload = routes.analyze_ticker_smart_rolls("AMD", bt, include_meta=True, current_user=admin)

    assert payload["symbol"] == "AMD"
    assert payload["is_stale"] is False
    assert len(payload["suggestions"]) == 2
    assert payload["suggestions"][0]["strike"] == 200


def test_analyze_ticker_smart_rolls_include_meta_stale_queues_refresh():
    admin = User(username="u", role="admin", disabled=False)
    bt = BackgroundTasks()
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.services.roll_service.RollService") as mock_roll_cls:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "_last_persisted_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
        }
        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "snap1"}
        mock_db.ibkr_holdings.find.return_value = [{"symbol": "AMD", "secType": "OPT"}]
        mock_roll_cls.return_value.analyze_portfolio_rolls.return_value = []

        payload = routes.analyze_ticker_smart_rolls("AMD", bt, include_meta=True, current_user=admin)

    assert payload["is_stale"] is True
    assert payload["refresh_queued"] is True
    assert len(bt.tasks) == 1


def test_get_data_freshness_config_reads_system_config_overrides():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {"_id": "data_freshness_config", "price_open_min": 25}
        payload = routes.get_data_freshness_config(admin)
    assert payload.price_open_min == 25
    assert payload.mixed_open_min == 30


def test_update_data_freshness_config_requires_admin():
    basic = User(username="u", role="basic", disabled=False)
    config = routes.DataFreshnessConfig()
    try:
        routes.update_data_freshness_config(config, basic)
        assert False, "expected HTTPException"
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 403


def test_update_data_freshness_config_persists_values():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {"_id": "data_freshness_config", "price_open_min": 40}
        payload = routes.update_data_freshness_config(
            routes.DataFreshnessConfig(price_open_min=40),
            admin,
        )
    assert payload.price_open_min == 40
    mock_db.system_config.update_one.assert_called_once()


def test_get_ticker_analysis_sanitizes_nan_values_to_avoid_500():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "Current Price": math.nan,
            "Company Name": "AMD",
            "profile": {"news": []},
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        payload = routes.get_ticker_analysis("AMD", bt, admin)
    assert payload["found"] is True
    assert payload["data"]["Current Price"] is None
