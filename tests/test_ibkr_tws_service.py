import logging
import threading
from types import SimpleNamespace

import app.services.ibkr_tws_service as tws_module
from app.services.ibkr_tws_service import IBKRTWSApp, IBKRTWSService


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
    assert kwargs["upsert"] is True


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
