import logging
from types import SimpleNamespace

import app.services.ibkr_tws_service as tws_module
from app.services.ibkr_tws_service import IBKRTWSApp, IBKRTWSService


class FakeApp:
    def __init__(self) -> None:
        self.positions = {}
        self.account_values = {}
        self.connected = False
        self.connect_calls: list[tuple[str, int, int]] = []
        self.req_positions_called = False
        self.disconnect_called = False

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connect_calls.append((host, port, client_id))
        self.connected = True

    def run(self) -> None:
        return None

    def reqPositions(self) -> None:
        self.req_positions_called = True

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
