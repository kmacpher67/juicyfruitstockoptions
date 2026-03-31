import asyncio
from unittest.mock import MagicMock, patch

from app.api import trades
from app.models import User


def _admin_user():
    return User(username="testuser", role="admin", disabled=False)


def test_get_trades_endpoint():
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 150.0, "DateTime": "20240101"},
        {"TradeID": "2", "Symbol": "GOOG", "Quantity": 5, "TradePrice": 2000.0, "DateTime": "20240102"},
    ]

    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_find = MagicMock()
        mock_find.sort.return_value.skip.return_value.limit.return_value = mock_cursor
        mock_db.ibkr_trades.find.return_value = mock_find
        mock_db.ibkr_dividends.find.return_value.limit.return_value = []

        data = asyncio.run(trades.get_trades(current_user=_admin_user()))

    assert len(data) == 2
    assert data[0].symbol == "GOOG"


def test_get_analysis_endpoint():
    mock_cursor = [
        {"TradeID": "1", "Symbol": "AAPL", "Quantity": 10, "TradePrice": 100.0, "DateTime": "20240101"},
        {"TradeID": "2", "Symbol": "AAPL", "Quantity": -10, "TradePrice": 110.0, "DateTime": "20240102"},
    ]

    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.find.return_value.sort.return_value = mock_cursor
        mock_db.ibkr_dividends.find.return_value = []

        data = asyncio.run(trades.get_trade_analysis(symbol="AAPL", current_user=_admin_user()))

    assert "trades" in data
    assert "metrics" in data
    assert data["metrics"].total_pl == 100.0
    assert data["metrics"].win_rate == 100.0


def test_get_trade_live_status_endpoint():
    fake_tws_service = MagicMock()
    fake_tws_service.get_live_status.return_value = {
        "connected": True,
        "connection_state": "connected",
        "diagnosis": "IBKR TWS API session connected.",
        "last_execution_update": "2026-03-31T12:15:00",
        "tws_enabled": True,
    }

    with patch("app.api.trades.MongoClient") as mock_client, patch(
        "app.api.trades.get_ibkr_tws_service", return_value=fake_tws_service
    ):
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.count_documents.return_value = 3
        mock_db.ibkr_trades.find_one.return_value = {
            "trade_id": "abc123",
            "source": "tws_live",
            "trade_date": "20260331",
            "date_time": "20260331 12:14:59",
            "last_tws_update": "2026-03-31T12:15:00",
        }

        data = asyncio.run(trades.get_trade_live_status(current_user=_admin_user()))

    assert data["connection_state"] == "connected"
    assert data["today_live_trade_count"] == 3
    assert data["latest_live_trade_at"] == "2026-03-31T12:15:00"
    assert data["last_failure_reason"] == "IBKR TWS API session connected."
    assert data["last_failure_at"] is None


def test_get_trade_live_status_exposes_last_failure_details():
    fake_tws_service = MagicMock()
    fake_tws_service.get_live_status.return_value = {
        "connected": False,
        "connection_state": "handshake_failed",
        "diagnosis": "TCP socket is reachable, but the IBKR API handshake did not complete.",
        "last_error": {
            "error_code": 504,
            "error": "Not connected",
            "timestamp": "2026-03-31T12:19:00",
        },
        "last_execution_update": None,
        "tws_enabled": True,
    }

    with patch("app.api.trades.MongoClient") as mock_client, patch(
        "app.api.trades.get_ibkr_tws_service", return_value=fake_tws_service
    ):
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.count_documents.return_value = 0
        mock_db.ibkr_trades.find_one.return_value = None

        data = asyncio.run(trades.get_trade_live_status(current_user=_admin_user()))

    assert data["connection_state"] == "handshake_failed"
    assert data["last_failure_reason"] == "Not connected"
    assert data["last_failure_at"] == "2026-03-31T12:19:00"


def test_get_live_trades_endpoint():
    live_docs = [
        {
            "trade_id": "exec_2",
            "symbol": "AAPL",
            "account_id": "DU123456",
            "trade_date": "20260331",
            "date_time": "20260331 12:15:00",
            "quantity": 5,
            "price": 201.0,
            "buy_sell": "BOT",
            "source": "tws_live",
        },
        {
            "trade_id": "exec_1",
            "symbol": "MSFT",
            "account_id": "DU123456",
            "trade_date": "20260331",
            "date_time": "20260331 09:35:00",
            "quantity": 2,
            "price": 410.5,
            "buy_sell": "SLD",
            "source": "tws_live",
        },
    ]

    with patch("app.api.trades.MongoClient") as mock_client:
        mock_db = mock_client.return_value.get_default_database.return_value
        mock_db.ibkr_trades.find.return_value.sort.return_value = live_docs

        data = asyncio.run(trades.get_live_trades(current_user=_admin_user()))

    assert len(data) == 2
    assert data[0].trade_id == "exec_2"
    assert data[0].source == "tws_live"


def test_today_live_trade_query_prefers_trade_date():
    query = trades._today_live_trade_query("20260331")

    assert query["source"] == "tws_live"
    assert {"trade_date": "20260331"} in query["$or"]
    assert {"date_time": {"$regex": "^20260331"}} in query["$or"]
