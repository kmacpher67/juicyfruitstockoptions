import logging
import threading
from types import SimpleNamespace

import pytest

import app.services.ibkr_tws_service as tws_module
from app.services.ibkr_tws_service import (
    IBKRTWSApp,
    IBKRTWSService,
    _normalize_execution_time,
)


class FakeApp:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.positions = {}
        self.account_values = {}
        self.executions = {}
        self.connected = False
        self.connect_calls: list[tuple[str, int, int]] = []
        self.req_positions_called = False
        self.req_account_updates_calls: list[tuple[bool, str]] = []
        self.req_executions_calls: list[tuple[int, object]] = []
        self.disconnect_called = False
        self.managed_accounts = []
        self.next_valid_order_id = 1
        self.position_snapshot_complete = False
        self.execution_snapshot_complete = False
        self.last_position_update = None
        self.last_account_value_update = None
        self.last_execution_update = None
        self.last_error = None
        self.last_status = None

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connect_calls.append((host, port, client_id))
        self.connected = True

    def run(self) -> None:
        return None

    def reqPositions(self) -> None:
        self.req_positions_called = True

    def reqAccountUpdates(self, subscribe: bool, account_code: str) -> None:
        self.req_account_updates_calls.append((subscribe, account_code))

    def reqExecutions(self, req_id: int, execution_filter: object) -> None:
        self.req_executions_calls.append((req_id, execution_filter))

    def disconnect(self) -> None:
        self.disconnect_called = True
        self.connected = False

    def isConnected(self) -> bool:
        return self.connected


def test_connect_starts_app_and_requests_positions(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    service = IBKRTWSService(
        host="ib-gateway",
        port=4002,
        client_id=7,
        enabled=True,
        app_factory=FakeApp,
        sleep_fn=lambda _: None,
    )
    monkeypatch.setattr(
        service,
        "_probe_socket",
        lambda timeout_seconds=1.0: {
            "host": "ib-gateway",
            "port": 4002,
            "timeout_seconds": timeout_seconds,
            "tcp_connectable": True,
            "error": None,
            "local_address": "172.18.0.4:45000",
        },
    )

    connected = service.connect()

    assert connected is True
    assert service.is_connected() is True
    assert service.app is not None
    assert service.app.connect_calls == [("ib-gateway", 4002, 7)]
    assert service.app.req_positions_called is True
    assert service._thread is not None
    assert service._thread.daemon is True


def test_position_and_account_callbacks_capture_state():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="AAPL",
        secType="STK",
        exchange="SMART",
        currency="USD",
    )

    app.position("DU123456", contract, 10, 150.25)
    app.updateAccountValue("NetLiquidation", "25000.50", "USD", "DU123456")

    positions = list(app.positions.values())
    assert len(positions) == 1
    assert positions[0]["symbol"] == "AAPL"
    assert positions[0]["position"] == 10
    assert positions[0]["avg_cost"] == 150.25

    account_value = app.account_values[("DU123456", "NetLiquidation")]
    assert account_value["value"] == "25000.50"
    assert account_value["currency"] == "USD"


def test_managed_accounts_subscribe_to_account_updates():
    app = IBKRTWSApp()
    calls = []
    app.reqAccountUpdates = lambda subscribe, account: calls.append((subscribe, account))

    app.managedAccounts("DU123456,DU999999")

    assert calls == [(True, "DU123456"), (True, "DU999999")]


def test_informational_tws_status_does_not_set_last_error():
    app = IBKRTWSApp()

    app.error(-1, 2104, "Market data farm connection is OK:usfarm")

    assert app.last_error is None
    assert app.last_status is not None
    assert app.last_status["error_code"] == 2104


def test_position_callback_subscribes_account_updates_once():
    app = IBKRTWSApp()
    calls = []
    app.reqAccountUpdates = lambda subscribe, account: calls.append((subscribe, account))
    contract = SimpleNamespace(symbol="AAPL", secType="STK", exchange="SMART", currency="USD")

    app.position("DU123456", contract, 10, 150.25)
    app.position("DU123456", contract, 11, 150.25)

    assert calls == [(True, "DU123456")]


def test_get_account_values_filters_by_account(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.account_values = {
        ("DU123456", "NetLiquidation"): {"value": "25000.50"},
        ("DU123456", "AvailableFunds"): {"value": "5000.00"},
        ("DU999999", "NetLiquidation"): {"value": "125.00"},
    }
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app

    values = service.get_account_values("DU123456")

    assert values == {
        "NetLiquidation": {"value": "25000.50"},
        "AvailableFunds": {"value": "5000.00"},
    }


def test_execution_and_commission_callbacks_capture_state():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="AAPL",
        localSymbol="AAPL",
        secType="STK",
        exchange="SMART",
        currency="USD",
    )
    execution = SimpleNamespace(
        execId="0001",
        acctNumber="DU123456",
        side="BOT",
        shares=10,
        price=200.5,
        avgPrice=200.5,
        cumQty=10,
        orderId=77,
        permId=88,
        clientId=1,
        time="20260330 15:45:00 US/Eastern",
        lastLiquidity=1,
    )
    commission_report = SimpleNamespace(
        execId="0001",
        commission=1.25,
        currency="USD",
        realizedPNL=12.5,
        yield_=0.0,
        yieldRedemptionDate=0,
    )

    app.execDetails(9001, contract, execution)
    app.commissionReport(commission_report)
    app.execDetailsEnd(9001)

    stored = app.executions["0001"]
    assert stored["symbol"] == "AAPL"
    assert stored["account"] == "DU123456"
    assert stored["buy_sell"] == "BOT"
    assert stored["commission"] == 1.25
    assert stored["realized_pnl"] == 12.5
    assert app.execution_snapshot_complete is True


def test_refresh_executions_requests_tws_snapshot(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app

    requested = service.refresh_executions(account="DU123456", req_id=9002)

    assert requested is True
    assert len(fake_app.req_executions_calls) == 1
    req_id, execution_filter = fake_app.req_executions_calls[0]
    assert req_id == 9002
    assert getattr(execution_filter, "acctCode") == "DU123456"


def test_live_status_reports_handshake_failure_when_socket_is_reachable(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = False
    fake_app.next_valid_order_id = None
    fake_app.last_error = {
        "error_code": 504,
        "error": "Not connected",
        "timestamp": "2026-03-31T12:45:22+00:00",
    }
    service = IBKRTWSService(
        host="host.docker.internal",
        port=7496,
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app
    monkeypatch.setattr(
        service,
        "_probe_socket",
        lambda timeout_seconds=1.0: {
            "host": "host.docker.internal",
            "port": 7496,
            "timeout_seconds": timeout_seconds,
            "tcp_connectable": True,
            "error": None,
            "local_address": "172.18.0.4:40506",
        },
    )

    status = service.get_live_status()

    assert status["connected"] is False
    assert status["socket_connectable"] is True
    assert status["connection_state"] == "handshake_failed"
    assert "handshake did not complete" in status["diagnosis"]
    assert "Last IBKR error: Not connected" in status["diagnosis"]
    assert status["last_error"]["error_code"] == 504


def test_live_status_reports_disconnected_when_socket_is_reachable_but_no_attempt(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    service = IBKRTWSService(
        host="host.docker.internal",
        port=7496,
        enabled=True,
        app_factory=FakeApp,
        sleep_fn=lambda _: None,
    )
    monkeypatch.setattr(
        service,
        "_probe_socket",
        lambda timeout_seconds=1.0: {
            "host": "host.docker.internal",
            "port": 7496,
            "timeout_seconds": timeout_seconds,
            "tcp_connectable": True,
            "error": None,
            "local_address": "172.18.0.4:40506",
        },
    )

    status = service.get_live_status()

    assert status["connection_state"] == "disconnected"
    assert status["handshake_attempted"] is False


def test_upsert_executions_to_db_maps_trade_fields(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.executions = {
        "0001": {
            "exec_id": "0001",
            "account": "DU123456",
            "symbol": "AAPL",
            "underlying_symbol": "AAPL",
            "date_time": "20260330 15:45:00 US/Eastern",
            "quantity": 10,
            "price": 200.5,
            "commission": 1.25,
            "realized_pnl": 12.5,
            "buy_sell": "BOT",
            "sec_type": "STK",
            "exchange": "SMART",
            "currency": "USD",
            "last_update": "2026-03-30T19:45:00+00:00",
        }
    }
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app
    mock_db = SimpleNamespace(ibkr_trades=SimpleNamespace(update_one=lambda *args, **kwargs: None))

    calls = []

    def _capture_update_one(*args, **kwargs):
        calls.append((args, kwargs))

    mock_db.ibkr_trades.update_one = _capture_update_one

    upserted = service.upsert_executions_to_db(db=mock_db)

    assert upserted == 1
    args, kwargs = calls[0]
    assert args[0] == {"trade_id": "0001"}
    stored_doc = args[1]["$set"]
    assert stored_doc["source"] == "tws_live"
    assert stored_doc["trade_id"] == "0001"
    assert stored_doc["account_id"] == "DU123456"
    assert stored_doc["asset_class"] == "STK"
    assert stored_doc["trade_date"] == "20260330"
    assert stored_doc["quantity"] == 10
    assert kwargs["upsert"] is True


def test_normalize_execution_time_handles_tz_suffix():
    normalized, trade_date = _normalize_execution_time("2026-03-31 14:04:16 US/Eastern")

    assert normalized == "20260331 14:04:16"
    assert trade_date == "20260331"


def test_exec_details_normalizes_sell_side_and_trade_date():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="AMD",
        localSymbol="AMD   260402C00202500",
        secType="OPT",
        exchange="PHLX",
        currency="USD",
    )
    execution = SimpleNamespace(
        execId="abc123",
        acctNumber="U280132",
        side="SLD",
        shares=1,
        price=3.10,
        avgPrice=3.10,
        cumQty=1,
        orderId=77,
        permId=99,
        clientId=5,
        time="2026-03-31 14:04:16 US/Eastern",
        lastLiquidity=2,
    )

    app.execDetails(9001, contract, execution)

    stored = app.executions["abc123"]
    assert stored["buy_sell"] == "SLD"
    assert stored["normalized_buy_sell"] == "SELL"
    assert stored["date_time"] == "20260331 14:04:16"
    assert stored["trade_date"] == "20260331"
    assert stored["signed_quantity"] == -1


def test_error_callback_records_last_error(caplog):
    app = IBKRTWSApp()

    with caplog.at_level(logging.ERROR):
        app.error(42, 504, "Not connected")

    assert app.last_error is not None
    assert app.last_error["req_id"] == 42
    assert app.last_error["error_code"] == 504
    assert "Not connected" in caplog.text


def test_disabled_service_is_graceful_noop():
    service = IBKRTWSService(enabled=False, app_factory=FakeApp)

    assert service.connect() is False
    assert service.is_connected() is False
    assert service.get_positions() == []
    assert service.get_account_values("DU123456") == {}
    service.disconnect()
