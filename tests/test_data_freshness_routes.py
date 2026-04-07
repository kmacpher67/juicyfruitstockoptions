from datetime import datetime, timedelta, timezone
import math
from unittest.mock import patch
from pydantic import ValidationError

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


def test_find_stock_data_by_symbol_ignores_non_dict_records():
    fake_db = type("DB", (), {})()
    fake_db.stock_data = type("Collection", (), {})()
    fake_db.stock_data.find_one = lambda *args, **kwargs: object()

    stock, query, symbol = routes._find_stock_data_by_symbol(fake_db, "aapl")  # pylint: disable=protected-access

    assert stock is None
    assert symbol == "AAPL"
    assert query == {"Ticker": "AAPL"}


def test_evaluate_stock_data_freshness_respects_system_config_threshold_override():
    stock = {"_last_persisted_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()}
    fake_db = type("DB", (), {})()
    fake_db.system_config = type("Collection", (), {})()
    fake_db.system_config.find_one = lambda query: {"price_open_min": 60}

    with patch("app.api.routes._is_us_equity_market_session", return_value=True):
        freshness = routes._evaluate_stock_data_freshness(stock, tier="price", db=fake_db)  # pylint: disable=protected-access
    assert freshness["is_stale"] is False


def test_is_us_equity_market_session_closed_on_holiday():
    # July 4, 2025 is an NYSE holiday (Friday).
    holiday_utc = datetime(2025, 7, 4, 15, 0, tzinfo=timezone.utc)  # 11:00 ET
    assert routes._is_us_equity_market_session(holiday_utc) is False  # pylint: disable=protected-access


def test_is_us_equity_market_session_uses_early_close_window():
    # Day after Thanksgiving (Nov 28, 2025) is an early-close day (1:00 PM ET).
    before_close_utc = datetime(2025, 11, 28, 17, 0, tzinfo=timezone.utc)  # 12:00 ET
    after_close_utc = datetime(2025, 11, 28, 19, 0, tzinfo=timezone.utc)   # 14:00 ET
    assert routes._is_us_equity_market_session(before_close_utc) is True  # pylint: disable=protected-access
    assert routes._is_us_equity_market_session(after_close_utc) is False  # pylint: disable=protected-access


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


def test_get_ticker_analysis_uses_snapshot_freshness_when_stock_record_missing():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    recent_iso = datetime.now(timezone.utc).isoformat()
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        mock_db.instrument_snapshot.find_one.return_value = {
            "instrument_key": "STK:AAPL",
            "symbol": "AAPL",
            "_last_persisted_at": recent_iso,
            "source": "stock_live_comparison",
        }
        payload = routes.get_ticker_analysis("AAPL", bt, admin)

    assert payload["found"] is False
    assert payload["is_stale"] is False
    assert payload["data_source"] == "stock_live_comparison"


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
    query = mock_db.instrument_price_history.find.call_args.args[0]
    assert {"instrument_key": "STK:AAPL"} in query["$or"]
    assert {"instrument_key": "AAPL"} in query["$or"]


def test_get_ticker_price_history_uses_snapshot_freshness_when_stock_missing():
    admin = User(username="u", role="admin", disabled=False)
    recent_iso = datetime.now(timezone.utc).isoformat()
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        mock_db.instrument_snapshot.find_one.return_value = {
            "instrument_key": "STK:AAPL",
            "symbol": "AAPL",
            "_last_persisted_at": recent_iso,
            "source": "stock_live_comparison",
        }
        mock_cursor = mock_db.instrument_price_history.find.return_value
        mock_cursor.sort.return_value.limit.return_value = []

        payload = routes.get_ticker_price_history("AAPL", admin, limit=50)

    assert payload["is_stale"] is False
    assert payload["data_source"] == "stock_live_comparison"


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


def test_get_ticker_news_prefers_cached_profile_news_db_first():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.services.news_service.NewsService") as mock_news_cls:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "_last_persisted_at": datetime.now(timezone.utc).isoformat(),
            "profile": {"news": [{"title": "cached-1"}, {"title": "cached-2"}]},
        }
        payload = routes.get_ticker_news("AMD", bt, admin, limit=1, include_meta=True)

    assert payload["symbol"] == "AMD"
    assert len(payload["news"]) == 1
    assert payload["news"][0]["title"] == "cached-1"
    assert payload["is_stale"] is False
    mock_news_cls.assert_not_called()


def test_get_ticker_news_falls_back_to_live_when_cache_missing():
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client, patch("app.services.news_service.NewsService") as mock_news_cls:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = None
        mock_news_cls.return_value.fetch_news_for_ticker.return_value = [{"title": "live-news"}]

        payload = routes.get_ticker_news("AMD", bt, admin, limit=5, include_meta=True)

    assert payload["symbol"] == "AMD"
    assert payload["news"][0]["title"] == "live-news"
    assert payload["data_source"] == "yfinance_live"
    assert payload["stale_reason"] == "db_record_missing"


def test_endpoint_freshness_tiers_apply_different_thresholds():
    stale_20m = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    bt = BackgroundTasks()
    admin = User(username="u", role="admin", disabled=False)
    config = {
        "_id": "data_freshness_config",
        "price_open_min": 10,
        "price_closed_min": 10,
        "mixed_open_min": 30,
        "mixed_closed_min": 30,
        "profile_open_min": 120,
        "profile_closed_min": 120,
    }
    stock_doc = {
        "Ticker": "AMD",
        "_last_persisted_at": stale_20m,
        "Current Price": 190.0,
        "Company Name": "AMD",
        "profile": {"news": [{"title": "cached-news"}]},
    }

    with patch("app.api.routes.MongoClient") as mock_client, patch(
        "app.api.routes._is_us_equity_market_session", return_value=True
    ):
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.stock_data.find_one.return_value = stock_doc
        mock_db.system_config.find_one.return_value = config

        ticker_payload = routes.get_ticker_analysis("AMD", bt, admin)
        opportunity_payload = routes.get_opportunity_analysis("AMD", bt, admin)
        news_payload = routes.get_ticker_news("AMD", bt, admin, include_meta=True)

    assert ticker_payload["is_stale"] is False  # mixed tier (30m)
    assert opportunity_payload["is_stale"] is True  # price tier (10m)
    assert news_payload["is_stale"] is False  # profile tier (120m)


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


def test_data_freshness_config_rejects_non_positive_values():
    try:
        routes.DataFreshnessConfig(price_open_min=0)
        assert False, "expected ValidationError"
    except Exception as exc:
        assert isinstance(exc, ValidationError)


def test_get_stock_analysis_http_config_reads_system_config_overrides():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {
            "_id": "stock_analysis_http_config",
            "download_batch_size": 4,
            "batch_pause_sec": 1.75,
            "request_throttle_interval_sec": 0.6,
            "scheduler_sharding_enabled": True,
            "scheduler_shard_size": 12,
            "scheduler_shard_pause_sec": 4.5,
        }
        payload = routes.get_stock_analysis_http_config(admin)
    assert payload.download_batch_size == 4
    assert payload.batch_pause_sec == 1.75
    assert payload.request_throttle_interval_sec == 0.6
    assert payload.scheduler_sharding_enabled is True
    assert payload.scheduler_shard_size == 12
    assert payload.scheduler_shard_pause_sec == 4.5


def test_get_stock_analysis_http_config_coerces_invalid_values():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {
            "_id": "stock_analysis_http_config",
            "download_batch_size": "oops",
            "batch_pause_sec": -5,
            "request_throttle_interval_sec": None,
            "scheduler_sharding_enabled": "yes",
            "scheduler_shard_size": "bad",
            "scheduler_shard_pause_sec": -7,
        }
        payload = routes.get_stock_analysis_http_config(admin)
    assert payload.download_batch_size == 6
    assert payload.batch_pause_sec == 0.0
    assert payload.request_throttle_interval_sec == 1.5
    assert payload.scheduler_sharding_enabled is True
    assert payload.scheduler_shard_size == 25
    assert payload.scheduler_shard_pause_sec == 0.0


def test_update_stock_analysis_http_config_requires_admin():
    basic = User(username="u", role="basic", disabled=False)
    config = routes.StockAnalysisHttpConfig()
    try:
        routes.update_stock_analysis_http_config(config, basic)
        assert False, "expected HTTPException"
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 403


def test_update_stock_analysis_http_config_persists_values():
    admin = User(username="u", role="admin", disabled=False)
    with patch("app.api.routes.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.system_config.find_one.return_value = {
            "_id": "stock_analysis_http_config",
            "download_batch_size": 9,
            "batch_pause_sec": 2.5,
            "request_throttle_interval_sec": 1.0,
            "scheduler_sharding_enabled": True,
            "scheduler_shard_size": 10,
            "scheduler_shard_pause_sec": 3.0,
        }
        payload = routes.update_stock_analysis_http_config(
            routes.StockAnalysisHttpConfig(
                download_batch_size=9,
                batch_pause_sec=2.5,
                request_throttle_interval_sec=1.0,
                scheduler_sharding_enabled=True,
                scheduler_shard_size=10,
                scheduler_shard_pause_sec=3.0,
            ),
            admin,
        )
    assert payload.download_batch_size == 9
    assert payload.batch_pause_sec == 2.5
    assert payload.request_throttle_interval_sec == 1.0
    assert payload.scheduler_sharding_enabled is True
    assert payload.scheduler_shard_size == 10
    assert payload.scheduler_shard_pause_sec == 3.0
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
