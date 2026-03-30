import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import settings

try:
    from ibapi.client import EClient
    from ibapi.contract import Contract
    from ibapi.wrapper import EWrapper

    IBAPI_IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover - exercised indirectly in runtime only
    class EWrapper:  # type: ignore[no-redef]
        pass

    class EClient:  # type: ignore[no-redef]
        def __init__(self, wrapper: Any | None = None) -> None:
            self.wrapper = wrapper
            self._connected = False

        def connect(self, host: str, port: int, client_id: int) -> None:
            self._connected = True

        def run(self) -> None:
            return None

        def disconnect(self) -> None:
            self._connected = False

        def reqPositions(self) -> None:
            return None

        def reqAccountUpdates(self, subscribe: bool, account_code: str) -> None:
            return None

        def isConnected(self) -> bool:
            return self._connected

    class Contract:  # type: ignore[no-redef]
        symbol: str = ""
        secType: str = ""
        exchange: str = ""
        currency: str = ""

    IBAPI_IMPORT_ERROR = exc


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IBKRTWSApp(EWrapper, EClient):
    """IBKR TWS socket client that captures portfolio and account callbacks."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.logger = logger or logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self._lock = threading.RLock()
        self.positions: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.account_values: dict[tuple[str, str], dict[str, Any]] = {}
        self.connected = False
        self.connection_attempted_at: str | None = None
        self.connected_at: str | None = None
        self.last_callback_at: str | None = None
        self.position_snapshot_complete = False
        self.next_valid_order_id: int | None = None
        self.managed_accounts: list[str] = []
        self.last_position_update: str | None = None
        self.last_account_value_update: str | None = None
        self.last_error: dict[str, Any] | None = None
        self.account_update_subscriptions: set[str] = set()

    def _mark_callback(self) -> str:
        timestamp = _utc_now_iso()
        with self._lock:
            self.last_callback_at = timestamp
        return timestamp

    def _subscribe_account_updates(self, account: str) -> None:
        if not account:
            return

        with self._lock:
            if account in self.account_update_subscriptions:
                return
            self.account_update_subscriptions.add(account)

        try:
            self.reqAccountUpdates(True, account)
            self.logger.info("Subscribed to TWS account updates for %s.", account)
        except Exception:
            with self._lock:
                self.account_update_subscriptions.discard(account)
            self.logger.exception("Failed to subscribe to TWS account updates for %s.", account)

    def connectAck(self) -> None:
        timestamp = self._mark_callback()
        with self._lock:
            self.connected = True
            self.connected_at = timestamp
        self.logger.info("TWS API connection acknowledged.")

    def nextValidId(self, orderId: int) -> None:
        timestamp = self._mark_callback()
        with self._lock:
            self.connected = True
            self.connected_at = self.connected_at or timestamp
            self.next_valid_order_id = orderId
        self.logger.info("Received nextValidId=%s from TWS.", orderId)

    def managedAccounts(self, accountsList: str) -> None:
        timestamp = self._mark_callback()
        accounts = [account for account in accountsList.split(",") if account]
        with self._lock:
            self.connected = True
            self.connected_at = self.connected_at or timestamp
            self.managed_accounts = accounts
        self.logger.info("Received %s managed account(s) from TWS.", len(accounts))
        for account in accounts:
            self._subscribe_account_updates(account)

    def position(
        self,
        account: str,
        contract: Contract,
        position: float,
        avgCost: float,
    ) -> None:
        payload = {
            "account": account,
            "symbol": getattr(contract, "symbol", ""),
            "sec_type": getattr(contract, "secType", ""),
            "exchange": getattr(contract, "exchange", ""),
            "currency": getattr(contract, "currency", ""),
            "position": position,
            "avg_cost": avgCost,
            "last_update": self._mark_callback(),
        }
        key = (payload["account"], payload["symbol"], payload["sec_type"])
        with self._lock:
            self.connected = True
            self.connected_at = self.connected_at or payload["last_update"]
            self.positions[key] = payload
            self.last_position_update = payload["last_update"]
        self.logger.debug("Received position update for %s.", key)
        self._subscribe_account_updates(account)

    def positionEnd(self) -> None:
        timestamp = self._mark_callback()
        with self._lock:
            self.position_snapshot_complete = True
            self.connected = True
            self.connected_at = self.connected_at or timestamp
        self.logger.info("Completed position snapshot with %s positions.", len(self.positions))

    def updateAccountValue(
        self,
        key: str,
        val: str,
        currency: str,
        accountName: str,
    ) -> None:
        payload = {
            "key": key,
            "value": val,
            "currency": currency,
            "account": accountName,
            "last_update": self._mark_callback(),
        }
        with self._lock:
            self.connected = True
            self.connected_at = self.connected_at or payload["last_update"]
            self.account_values[(accountName, key)] = payload
            self.last_account_value_update = payload["last_update"]
        self.logger.debug("Received account value update for %s/%s.", accountName, key)

    def error(
        self,
        reqId: int,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = "",
    ) -> None:
        payload = {
            "req_id": reqId,
            "error_code": errorCode,
            "error": errorString,
            "advanced_order_reject_json": advancedOrderRejectJson,
            "timestamp": self._mark_callback(),
        }
        with self._lock:
            self.last_error = payload
        self.logger.error(
            "TWS API error reqId=%s code=%s message=%s",
            reqId,
            errorCode,
            errorString,
        )


class IBKRTWSService:
    """Thread-safe singleton-friendly wrapper around the IBKR TWS API client."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        *,
        enabled: bool | None = None,
        app_factory: Callable[[], IBKRTWSApp] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.enabled = settings.IBKR_TWS_ENABLED if enabled is None else enabled
        self.host = host or settings.IBKR_TWS_HOST
        self.port = settings.IBKR_TWS_PORT if port is None else port
        self.client_id = (
            settings.IBKR_TWS_CLIENT_ID if client_id is None else client_id
        )
        self._app_factory = app_factory or self._default_app_factory
        self._sleep_fn = sleep_fn or time.sleep
        self._lock = threading.RLock()
        self._app: IBKRTWSApp | None = None
        self._thread: threading.Thread | None = None

    def _default_app_factory(self) -> IBKRTWSApp:
        return IBKRTWSApp()

    def _is_disabled(self) -> bool:
        if not self.enabled:
            self.logger.info("IBKR TWS service is disabled by feature flag.")
            return True
        if IBAPI_IMPORT_ERROR is not None:
            self.logger.warning("IBKR TWS service unavailable because ibapi is not installed.")
            return True
        return False

    def connect(self) -> bool:
        if self._is_disabled():
            return False

        with self._lock:
            if self.is_connected():
                self.logger.info("IBKR TWS service is already connected.")
                return True

            app = self._app_factory()
            app.connection_attempted_at = _utc_now_iso()
            self._app = app
            app.connect(self.host, self.port, self.client_id)
            thread = threading.Thread(target=app.run, daemon=True)
            thread.start()
            self._sleep_fn(1)
            app.reqPositions()
            self._wait_for_connection_signal(app)

            self._thread = thread

        connected = self.is_connected()
        if connected:
            self.logger.info("Connected to IBKR TWS at %s:%s.", self.host, self.port)
        else:
            self.logger.warning(
                "TWS connect attempt did not reach a confirmed connected state for %s:%s.",
                self.host,
                self.port,
            )
        return connected

    def _wait_for_connection_signal(
        self,
        app: IBKRTWSApp,
        timeout_seconds: float = 3.0,
        poll_interval: float = 0.1,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            with app._lock:
                connected = bool(
                    app.connected
                    or app.next_valid_order_id is not None
                    or app.managed_accounts
                    or app.positions
                    or app.position_snapshot_complete
                )
                fatal_error = (
                    app.last_error is not None
                    and int(app.last_error.get("error_code", 0)) == 504
                    and not connected
                )
            if connected or fatal_error:
                return
            self._sleep_fn(poll_interval)

    def disconnect(self) -> None:
        if self._is_disabled():
            return

        with self._lock:
            app = self._app
            self._app = None
            self._thread = None

        if app is None:
            return

        app.disconnect()
        if hasattr(app, "connected"):
            app.connected = False
        self.logger.info("Disconnected from IBKR TWS.")

    def get_positions(self) -> list[dict[str, Any]]:
        if self._is_disabled():
            return []

        with self._lock:
            if self._app is None:
                return []
            return list(self._app.positions.values())

    def get_account_values(self, account: str) -> dict[str, dict[str, Any]]:
        if self._is_disabled():
            return {}

        with self._lock:
            if self._app is None:
                return {}
            return {
                key_name: payload
                for (account_name, key_name), payload in self._app.account_values.items()
                if account_name == account
            }

    def is_connected(self) -> bool:
        with self._lock:
            if self._app is None:
                return False
            app_connected = getattr(self._app, "connected", False)
            callback_connected = bool(
                getattr(self._app, "next_valid_order_id", None) is not None
                or getattr(self._app, "managed_accounts", [])
                or getattr(self._app, "positions", {})
                or getattr(self._app, "position_snapshot_complete", False)
            )
            client_connected = getattr(self._app, "isConnected", None)
            if callable(client_connected):
                try:
                    return bool(client_connected() or app_connected or callback_connected)
                except Exception:
                    return bool(app_connected or callback_connected)
            return bool(app_connected or callback_connected)

    @property
    def app(self) -> IBKRTWSApp | None:
        with self._lock:
            return self._app

    def get_live_status(self) -> dict[str, Any]:
        with self._lock:
            app = self._app
            positions = list(app.positions.values()) if app is not None else []
            last_position_update = None
            if positions:
                timestamps = [
                    position.get("last_update")
                    for position in positions
                    if position.get("last_update")
                ]
                if timestamps:
                    last_position_update = max(timestamps)
            elif app is not None:
                last_position_update = getattr(app, "last_position_update", None)

            return {
                "connected": self.is_connected(),
                "host": self.host,
                "port": self.port,
                "client_id": self.client_id,
                "managed_accounts": list(getattr(app, "managed_accounts", [])) if app is not None else [],
                "next_valid_order_id": getattr(app, "next_valid_order_id", None) if app is not None else None,
                "connection_attempted_at": getattr(app, "connection_attempted_at", None) if app is not None else None,
                "connected_at": getattr(app, "connected_at", None) if app is not None else None,
                "last_callback_at": getattr(app, "last_callback_at", None) if app is not None else None,
                "position_snapshot_complete": getattr(app, "position_snapshot_complete", False) if app is not None else False,
                "last_position_update": last_position_update,
                "last_account_value_update": getattr(app, "last_account_value_update", None) if app is not None else None,
                "last_error": getattr(app, "last_error", None) if app is not None else None,
                "position_count": len(positions),
                "tws_enabled": bool(self.enabled and IBAPI_IMPORT_ERROR is None),
            }


_service_singleton: IBKRTWSService | None = None
_service_singleton_lock = threading.RLock()


def get_ibkr_tws_service() -> IBKRTWSService:
    global _service_singleton
    with _service_singleton_lock:
        if _service_singleton is None:
            _service_singleton = IBKRTWSService()
        return _service_singleton


def set_ibkr_tws_service(service: IBKRTWSService | None) -> None:
    global _service_singleton
    with _service_singleton_lock:
        _service_singleton = service
