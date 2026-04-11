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
        self.req_all_open_orders_called = False
        self.disconnect_called = False
        self.managed_accounts = []
        self.next_valid_order_id = 1
        self.position_snapshot_complete = False
        self.execution_snapshot_complete = False
        self.order_snapshot_complete = False
        self.last_position_update = None
        self.last_account_value_update = None
        self.last_execution_update = None
        self.last_order_update = None
        self.last_error = None
        self.last_status = None
        self.orders = {}

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

    def reqAllOpenOrders(self) -> None:
        self.req_all_open_orders_called = True

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
        localSymbol="AAPL",
        lastTradeDateOrContractMonth="",
        strike=0.0,
        right="",
        multiplier="1",
    )

    app.position("DU123456", contract, 10, 150.25)
    app.updateAccountValue("NetLiquidation", "25000.50", "USD", "DU123456")

    positions = list(app.positions.values())
    assert len(positions) == 1
    assert positions[0]["symbol"] == "AAPL"
    assert positions[0]["underlying_symbol"] == "AAPL"
    assert positions[0]["local_symbol"] == "AAPL"
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


def test_error_callback_supports_new_ibapi_signature_shape():
    app = IBKRTWSApp()

    app.error(-1, "2026-04-09 12:45:22", 504, "Not connected", "")

    assert app.last_error is not None
    assert app.last_error["error_code"] == 504
    assert app.last_error["error"] == "Not connected"


def test_position_callback_subscribes_account_updates_once():
    app = IBKRTWSApp()
    calls = []
    app.reqAccountUpdates = lambda subscribe, account: calls.append((subscribe, account))
    contract = SimpleNamespace(
        symbol="AAPL",
        secType="STK",
        exchange="SMART",
        currency="USD",
        localSymbol="AAPL",
        lastTradeDateOrContractMonth="",
        strike=0.0,
        right="",
        multiplier="1",
    )

    app.position("DU123456", contract, 10, 150.25)
    app.position("DU123456", contract, 11, 150.25)

    assert calls == [(True, "DU123456")]


def test_option_position_callback_captures_contract_details():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="AMD",
        localSymbol="AMD   260402C00202500",
        secType="OPT",
        exchange="SMART",
        currency="USD",
        lastTradeDateOrContractMonth="20260402",
        strike=202.5,
        right="C",
        multiplier="100",
    )

    app.position("U110638", contract, -1, 5.25)

    stored = list(app.positions.values())[0]
    assert stored["symbol"] == "AMD"
    assert stored["underlying_symbol"] == "AMD"
    assert stored["local_symbol"] == "AMD   260402C00202500"
    assert stored["last_trade_date"] == "20260402"
    assert stored["strike"] == 202.5
    assert stored["right"] == "C"
    assert stored["multiplier"] == "100"


def test_option_positions_with_same_underlying_do_not_overwrite_each_other():
    app = IBKRTWSApp()
    near_contract = SimpleNamespace(
        symbol="AMD",
        localSymbol="AMD   260402C00202500",
        secType="OPT",
        exchange="SMART",
        currency="USD",
        lastTradeDateOrContractMonth="20260402",
        strike=202.5,
        right="C",
        multiplier="100",
        conId=111111,
    )
    far_contract = SimpleNamespace(
        symbol="AMD",
        localSymbol="AMD   260410C00207500",
        secType="OPT",
        exchange="SMART",
        currency="USD",
        lastTradeDateOrContractMonth="20260410",
        strike=207.5,
        right="C",
        multiplier="100",
        conId=222222,
    )

    app.position("U110638", near_contract, -1, 5.25)
    app.position("U110638", far_contract, -1, 3.15)

    positions = list(app.positions.values())
    assert len(positions) == 2
    local_symbols = {position["local_symbol"] for position in positions}
    assert local_symbols == {"AMD   260402C00202500", "AMD   260410C00207500"}


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
    assert stored["action"] == "BOT"
    assert stored["raw_action"] == "BOT"
    assert stored["commission"] == 1.25
    assert stored["realized_pnl"] == 12.5
    assert app.execution_snapshot_complete is True


def test_exec_details_preserves_non_fill_action_values():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="ZETA",
        localSymbol="ZETA  260410C00015500",
        secType="OPT",
        exchange="OCC",
        currency="USD",
    )
    execution = SimpleNamespace(
        execId="expired001",
        acctNumber="U110638",
        side="EXPIRED",
        shares=1,
        price=0.0,
        avgPrice=0.0,
        cumQty=1,
        orderId=701,
        permId=9001,
        clientId=5,
        time="2026-04-10 22:17:14 US/Eastern",
        lastLiquidity=0,
    )

    app.execDetails(9001, contract, execution)

    stored = app.executions["expired001"]
    assert stored["buy_sell"] == "EXPIRED"
    assert stored["normalized_buy_sell"] == "EXPIRED"
    assert stored["action"] == "EXPIRED"
    assert stored["raw_action"] == "EXPIRED"
    assert stored["outcome_action"] == "EXPIRED"
    assert stored["underlying_symbol"] == "ZETA"


def test_commission_callback_supports_new_ibapi_commission_and_fees_field():
    app = IBKRTWSApp()
    app.executions["0002"] = {"exec_id": "0002", "symbol": "MSFT"}
    commission_report = SimpleNamespace(
        execId="0002",
        commissionAndFees=2.75,
        currency="USD",
        realizedPNL=8.5,
        yield_=0.0,
        yieldRedemptionDate=0,
    )

    app.commissionReport(commission_report)

    stored = app.executions["0002"]
    assert stored["commission"] == 2.75
    assert stored["realized_pnl"] == 8.5
    assert stored["commission_currency"] == "USD"


def test_open_order_and_order_status_callbacks_capture_state():
    app = IBKRTWSApp()
    contract = SimpleNamespace(
        symbol="AMD",
        localSymbol="AMD   260418C00115000",
        secType="OPT",
        exchange="SMART",
        currency="USD",
        lastTradeDateOrContractMonth="20260418",
        strike=115.0,
        right="C",
        multiplier="100",
        conId=123456,
    )
    order = SimpleNamespace(
        permId=9001,
        parentId=0,
        clientId=7,
        account="U110638",
        action="SELL",
        totalQuantity=2,
        orderType="LMT",
        tif="DAY",
        lmtPrice=1.55,
        auxPrice=0.0,
        openClose="O",
        orderRef="cover-amd",
    )
    order_state = SimpleNamespace(status="Submitted")

    app.openOrder(77, contract, order, order_state)
    app.orderStatus(77, "Submitted", 0, 2, 0.0, 9001, 0, 0.0, 7, "", 0.0)
    app.openOrderEnd()

    stored = app.orders["perm:9001"]
    assert stored["order_id"] == 77
    assert stored["perm_id"] == 9001
    assert stored["account_id"] == "U110638"
    assert stored["underlying_symbol"] == "AMD"
    assert stored["action"] == "SELL"
    assert stored["status"] == "Submitted"
    assert stored["remaining_quantity"] == 2
    assert stored["right"] == "C"
    assert app.order_snapshot_complete is True


def test_refresh_open_orders_requests_all_open_orders(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = True
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app

    requested = service.refresh_open_orders()

    assert requested is True
    assert fake_app.req_all_open_orders_called is True


def test_refresh_open_orders_returns_false_when_ibapi_request_raises(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = True

    def _boom():
        raise TypeError("serverVersion is None")

    fake_app.reqAllOpenOrders = _boom
    service = IBKRTWSService(enabled=True, app_factory=lambda: fake_app, sleep_fn=lambda _: None)
    service._app = fake_app

    requested = service.refresh_open_orders()

    assert requested is False


def test_upsert_open_orders_to_db_writes_ibkr_orders(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = True
    fake_app.orders = {
        "perm:9001": {
            "order_key": "perm:9001",
            "order_id": 77,
            "perm_id": 9001,
            "account_id": "U110638",
            "symbol": "AMD",
            "underlying_symbol": "AMD",
            "local_symbol": "AMD   260418C00115000",
            "sec_type": "OPT",
            "action": "SELL",
            "status": "Submitted",
            "total_quantity": 2,
            "remaining_quantity": 2,
            "multiplier": "100",
            "right": "C",
            "strike": 115.0,
            "last_update": "2026-04-02T12:00:00+00:00",
        }
    }
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app
    mock_db = SimpleNamespace(ibkr_orders=SimpleNamespace(update_one=lambda *args, **kwargs: None))

    update_calls = []
    mock_db.ibkr_orders.update_one = lambda *args, **kwargs: update_calls.append((args, kwargs))

    upserted = service.upsert_open_orders_to_db(db=mock_db)

    assert upserted == 1
    args, kwargs = update_calls[0]
    assert args[0] == {"order_key": "perm:9001"}
    assert args[1]["$set"]["source"] == "tws_open_order"
    assert args[1]["$set"]["account_id"] == "U110638"
    assert kwargs["upsert"] is True


def test_upsert_open_orders_reconciles_stale_rows_when_snapshot_complete(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = True
    fake_app.order_snapshot_complete = True
    fake_app.orders = {}
    service = IBKRTWSService(
        enabled=True,
        app_factory=lambda: fake_app,
        sleep_fn=lambda _: None,
    )
    service._app = fake_app

    update_many_calls = []
    mock_collection = SimpleNamespace(
        update_one=lambda *args, **kwargs: None,
        update_many=lambda *args, **kwargs: update_many_calls.append((args, kwargs))
        or SimpleNamespace(modified_count=3),
    )
    mock_db = SimpleNamespace(ibkr_orders=mock_collection)

    upserted = service.upsert_open_orders_to_db(db=mock_db)

    assert upserted == 0
    assert len(update_many_calls) == 1
    args, _ = update_many_calls[0]
    assert args[0]["source"] == "tws_open_order"
    assert args[1]["$set"]["status"] == "Inactive"
    assert args[1]["$set"]["remaining_quantity"] == 0.0
    assert args[1]["$set"]["stale_reconciled"] is True


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


def test_is_connected_requires_handshake_not_raw_socket_client(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.connected = False
    fake_app.next_valid_order_id = None
    fake_app.last_error = {
        "error_code": 504,
        "error": "Not connected",
        "timestamp": "2026-03-31T12:45:22+00:00",
    }
    fake_app.isConnected = lambda: True
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

    assert service.is_connected() is False
    assert service.get_live_status()["connection_state"] == "handshake_failed"


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
    assert stored_doc["source_stage"] == "provisional_realtime"
    assert stored_doc["record_status"] == "provisional"
    assert stored_doc["trade_id"] == "0001"
    assert stored_doc["account_id"] == "DU123456"
    assert stored_doc["asset_class"] == "STK"
    assert stored_doc["trade_date"] == "20260330"
    assert stored_doc["quantity"] == 10
    assert kwargs["upsert"] is True


def test_upsert_executions_to_db_preserves_raw_expiration_action(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.executions = {
        "expired001": {
            "exec_id": "expired001",
            "account": "U110638",
            "symbol": "ZETA",
            "underlying_symbol": "ZETA",
            "local_symbol": "ZETA  260410C00015500",
            "date_time": "20260410 22:17:14",
            "quantity": 1,
            "price": 0.0,
            "buy_sell": "EXPIRED",
            "action": "EXPIRED",
            "raw_action": "EXPIRED",
            "outcome_action": "EXPIRED",
            "sec_type": "OPT",
            "exchange": "OCC",
            "currency": "USD",
            "last_update": "2026-04-11T02:17:14+00:00",
        }
    }
    service = IBKRTWSService(enabled=True, app_factory=lambda: fake_app, sleep_fn=lambda _: None)
    service._app = fake_app
    mock_db = SimpleNamespace(ibkr_trades=SimpleNamespace(update_one=lambda *args, **kwargs: None))
    calls = []
    mock_db.ibkr_trades.update_one = lambda *args, **kwargs: calls.append((args, kwargs))

    upserted = service.upsert_executions_to_db(db=mock_db)

    assert upserted == 1
    stored_doc = calls[0][0][1]["$set"]
    assert stored_doc["buy_sell"] == "EXPIRED"
    assert stored_doc["action"] == "EXPIRED"
    assert stored_doc["raw_action"] == "EXPIRED"
    assert stored_doc["outcome_action"] == "EXPIRED"
    assert stored_doc["underlying_symbol"] == "ZETA"


def test_get_execution_diagnostics_summarizes_actions_and_outcomes(monkeypatch):
    monkeypatch.setattr(tws_module, "IBAPI_IMPORT_ERROR", None)
    fake_app = FakeApp()
    fake_app.executions = {
        "expired001": {
            "exec_id": "expired001",
            "account": "U110638",
            "symbol": "ZETA",
            "underlying_symbol": "ZETA",
            "local_symbol": "ZETA  260410C00015500",
            "date_time": "20260410 22:17:14",
            "buy_sell": "EXPIRED",
            "action": "EXPIRED",
            "raw_action": "EXPIRED",
            "source": "tws_live",
        },
        "assigned001": {
            "exec_id": "assigned001",
            "account": "U110638",
            "symbol": "T",
            "underlying_symbol": "T",
            "local_symbol": "T  260410P00028000",
            "date_time": "20260410 22:24:19",
            "buy_sell": "ASSIGNED",
            "action": "ASSIGNED",
            "raw_action": "ASSIGNED",
            "source": "tws_live",
        },
        "buy001": {
            "exec_id": "buy001",
            "account": "U110638",
            "symbol": "AAPL",
            "underlying_symbol": "AAPL",
            "date_time": "20260410 13:00:00",
            "buy_sell": "BOT",
            "action": "BOT",
            "raw_action": "BOT",
            "source": "tws_live",
        },
    }
    service = IBKRTWSService(enabled=True, app_factory=lambda: fake_app, sleep_fn=lambda _: None)
    service._app = fake_app

    diagnostics = service.get_execution_diagnostics(account="U110638")

    assert diagnostics["execution_count"] == 3
    assert diagnostics["action_counts"]["EXPIRED"] == 1
    assert diagnostics["action_counts"]["ASSIGNED"] == 1
    assert diagnostics["action_counts"]["BOT"] == 1
    assert len(diagnostics["outcome_rows"]) == 2
    assert diagnostics["outcome_rows"][0]["action"] == "ASSIGNED"


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
