import logging
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import settings

try:
    from ibapi.client import EClient
    from ibapi.commission_report import CommissionReport
    from ibapi.contract import Contract
    from ibapi.execution import Execution, ExecutionFilter
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

        def reqExecutions(self, req_id: int, execution_filter: Any) -> None:
            return None

        def isConnected(self) -> bool:
            return self._connected

    class Contract:  # type: ignore[no-redef]
        symbol: str = ""
        secType: str = ""
        exchange: str = ""
        currency: str = ""

    class Execution:  # type: ignore[no-redef]
        execId: str = ""
        acctNumber: str = ""
        side: str = ""
        shares: float = 0.0
        price: float = 0.0
        time: str = ""
        orderId: int = 0
        permId: int = 0
        clientId: int = 0
        avgPrice: float = 0.0
        cumQty: float = 0.0
        evRule: str = ""
        evMultiplier: float = 0.0
        modelCode: str = ""
        lastLiquidity: int = 0

    class ExecutionFilter:  # type: ignore[no-redef]
        acctCode: str = ""

    class CommissionReport:  # type: ignore[no-redef]
        execId: str = ""
        commission: float = 0.0
        currency: str = ""
        realizedPNL: float = 0.0
        yield_: float = 0.0
        yieldRedemptionDate: int = 0

    IBAPI_IMPORT_ERROR = exc


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_execution_time(raw_value: Any) -> tuple[str, str | None]:
    """Return a stable trade timestamp string and YYYYMMDD trade-date key."""
    if raw_value is None:
        return "", None

    value = str(raw_value).strip()
    if not value:
        return "", None

    compact_value = " ".join(value.split())
    parse_candidates = [
        ("%Y%m%d %H:%M:%S", compact_value),
        ("%Y%m%d-%H:%M:%S", compact_value),
        ("%Y-%m-%d %H:%M:%S", compact_value),
    ]

    if "T" in compact_value:
        iso_candidate = compact_value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
            normalized = parsed.strftime("%Y%m%d %H:%M:%S")
            return normalized, normalized[:8]
        except ValueError:
            pass

    if len(compact_value) >= 19:
        first_nineteen = compact_value[:19]
        parse_candidates.extend(
            [
                ("%Y-%m-%d %H:%M:%S", first_nineteen),
                ("%Y/%m/%d %H:%M:%S", first_nineteen),
            ]
        )

    for fmt, candidate in parse_candidates:
        try:
            parsed = datetime.strptime(candidate, fmt)
            normalized = parsed.strftime("%Y%m%d %H:%M:%S")
            return normalized, normalized[:8]
        except ValueError:
            continue

    digits_only = "".join(ch for ch in compact_value if ch.isdigit())
    if len(digits_only) >= 14:
        normalized = f"{digits_only[:8]} {digits_only[8:10]}:{digits_only[10:12]}:{digits_only[12:14]}"
        return normalized, normalized[:8]
    if len(digits_only) >= 8:
        return compact_value, digits_only[:8]

    return compact_value, None


def _normalize_execution_side(raw_value: Any) -> str:
    value = str(raw_value or "").strip().upper()
    if value in {"BOT", "BUY"}:
        return "BUY"
    if value in {"SLD", "SELL"}:
        return "SELL"
    return value


def _signed_execution_quantity(raw_quantity: Any, raw_side: Any) -> float:
    try:
        quantity = float(raw_quantity or 0)
    except (TypeError, ValueError):
        quantity = 0.0

    side = _normalize_execution_side(raw_side)
    if side == "SELL":
        return -abs(quantity)
    if side == "BUY":
        return abs(quantity)
    return quantity


INFO_ERROR_CODES = {2104, 2106, 2158}


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
        self.executions: dict[str, dict[str, Any]] = {}
        self.execution_snapshot_complete = False
        self.last_execution_update: str | None = None
        self.last_error: dict[str, Any] | None = None
        self.last_status: dict[str, Any] | None = None
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

    def execDetails(
        self,
        reqId: int,
        contract: Contract,
        execution: Execution,
    ) -> None:
        exec_id = getattr(execution, "execId", "")
        if not exec_id:
            self.logger.warning("Received execution update without execId for reqId=%s.", reqId)
            return

        timestamp = self._mark_callback()
        normalized_time, trade_date = _normalize_execution_time(getattr(execution, "time", ""))
        raw_side = getattr(execution, "side", "")
        payload = {
            "exec_id": exec_id,
            "req_id": reqId,
            "account": getattr(execution, "acctNumber", ""),
            "symbol": getattr(contract, "symbol", ""),
            "underlying_symbol": getattr(contract, "localSymbol", "") or getattr(contract, "symbol", ""),
            "sec_type": getattr(contract, "secType", ""),
            "exchange": getattr(contract, "exchange", ""),
            "currency": getattr(contract, "currency", ""),
            "buy_sell": raw_side,
            "normalized_buy_sell": _normalize_execution_side(raw_side),
            "quantity": getattr(execution, "shares", 0),
            "signed_quantity": _signed_execution_quantity(
                getattr(execution, "shares", 0),
                getattr(execution, "side", ""),
            ),
            "price": getattr(execution, "price", 0),
            "avg_price": getattr(execution, "avgPrice", 0),
            "cum_qty": getattr(execution, "cumQty", 0),
            "order_id": getattr(execution, "orderId", None),
            "perm_id": getattr(execution, "permId", None),
            "client_id": getattr(execution, "clientId", None),
            "date_time": normalized_time,
            "raw_execution_time": getattr(execution, "time", ""),
            "trade_date": trade_date,
            "last_liquidity": getattr(execution, "lastLiquidity", None),
            "last_update": timestamp,
            "source": "tws_live",
        }
        with self._lock:
            existing = self.executions.get(exec_id, {})
            merged = {**existing, **payload}
            self.executions[exec_id] = merged
            self.connected = True
            self.connected_at = self.connected_at or timestamp
            self.last_execution_update = timestamp
        self.logger.debug("Received execution update for execId=%s.", exec_id)

    def execDetailsEnd(self, reqId: int) -> None:
        timestamp = self._mark_callback()
        with self._lock:
            self.execution_snapshot_complete = True
            self.connected = True
            self.connected_at = self.connected_at or timestamp
        self.logger.info("Completed execution snapshot for reqId=%s with %s executions.", reqId, len(self.executions))

    def commissionReport(self, commissionReport: CommissionReport) -> None:
        exec_id = getattr(commissionReport, "execId", "")
        if not exec_id:
            self.logger.warning("Received commission report without execId.")
            return

        payload = {
            "commission": getattr(commissionReport, "commission", 0),
            "commission_currency": getattr(commissionReport, "currency", ""),
            "realized_pnl": getattr(commissionReport, "realizedPNL", 0),
            "yield": getattr(commissionReport, "yield_", 0),
            "yield_redemption_date": getattr(commissionReport, "yieldRedemptionDate", 0),
            "last_update": self._mark_callback(),
        }
        with self._lock:
            existing = self.executions.get(exec_id, {})
            self.executions[exec_id] = {**existing, **payload, "exec_id": exec_id}
            self.last_execution_update = payload["last_update"]
        self.logger.debug("Received commission report for execId=%s.", exec_id)

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
        if int(errorCode) in INFO_ERROR_CODES:
            with self._lock:
                self.last_status = payload
            self.logger.info(
                "TWS API status reqId=%s code=%s message=%s",
                reqId,
                errorCode,
                errorString,
            )
            return

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

    def _has_handshake_evidence(self, app: IBKRTWSApp | None) -> bool:
        if app is None:
            return False
        return bool(
            getattr(app, "connection_attempted_at", None)
            or getattr(app, "last_callback_at", None)
            or getattr(app, "last_error", None)
            or getattr(app, "last_status", None)
            or getattr(app, "next_valid_order_id", None) is not None
        )

    def _default_app_factory(self) -> IBKRTWSApp:
        return IBKRTWSApp()

    def _probe_socket(self, timeout_seconds: float = 1.0) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "timeout_seconds": timeout_seconds,
            "tcp_connectable": False,
            "error": None,
            "local_address": None,
        }
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout_seconds) as sock:
                payload["tcp_connectable"] = True
                local_host, local_port = sock.getsockname()[:2]
                payload["local_address"] = f"{local_host}:{local_port}"
        except OSError as exc:
            payload["error"] = str(exc)
        return payload

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
            socket_probe = self._probe_socket()
            if socket_probe["tcp_connectable"]:
                self.logger.info(
                    "TWS socket probe succeeded for %s:%s from %s.",
                    self.host,
                    self.port,
                    socket_probe.get("local_address"),
                )
            else:
                self.logger.warning(
                    "TWS socket probe failed for %s:%s: %s",
                    self.host,
                    self.port,
                    socket_probe.get("error"),
                )
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
                "TWS connect attempt did not reach a confirmed connected state for %s:%s. socket_connectable=%s last_error=%s",
                self.host,
                self.port,
                socket_probe.get("tcp_connectable"),
                self.get_live_status().get("last_error"),
            )
        return connected

    def ensure_connected(self) -> bool:
        if self._is_disabled():
            return False
        if self.is_connected():
            return True
        return self.connect()

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

    def refresh_executions(self, account: str | None = None, req_id: int = 9001) -> bool:
        if self._is_disabled():
            return False

        with self._lock:
            app = self._app
        if app is None or not self.is_connected():
            self.logger.warning("Cannot request executions because TWS is not connected.")
            return False

        execution_filter = ExecutionFilter()
        if account:
            setattr(execution_filter, "acctCode", account)

        with app._lock:
            app.execution_snapshot_complete = False
        app.reqExecutions(req_id, execution_filter)
        self.logger.info("Requested TWS executions for account=%s reqId=%s.", account or "*", req_id)
        return True

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

    def get_executions(self, account: str | None = None) -> list[dict[str, Any]]:
        if self._is_disabled():
            return []

        with self._lock:
            if self._app is None:
                return []
            executions = list(self._app.executions.values())

        if not account:
            return executions
        return [execution for execution in executions if execution.get("account") == account]

    def upsert_executions_to_db(self, db: Any | None = None, account: str | None = None) -> int:
        executions = self.get_executions(account=account)
        if not executions:
            return 0

        if db is None:
            from pymongo import MongoClient

            client = MongoClient(settings.MONGO_URI)
            db = client.get_default_database("stock_analysis")

        upserted = 0
        for execution in executions:
            exec_id = execution.get("exec_id")
            symbol = execution.get("symbol")
            if not exec_id or not symbol:
                continue
            normalized_time, derived_trade_date = _normalize_execution_time(
                execution.get("date_time") or execution.get("raw_execution_time")
            )
            trade_date = execution.get("trade_date") or derived_trade_date
            normalized_side = execution.get("normalized_buy_sell") or _normalize_execution_side(
                execution.get("buy_sell")
            )

            trade_doc = {
                "trade_id": exec_id,
                "account_id": execution.get("account"),
                "symbol": symbol,
                "underlying_symbol": execution.get("underlying_symbol") or symbol,
                "date_time": execution.get("date_time") or normalized_time,
                "trade_date": trade_date,
                "quantity": float(
                    execution.get("signed_quantity")
                    if execution.get("signed_quantity") is not None
                    else _signed_execution_quantity(
                        execution.get("quantity") or 0,
                        execution.get("buy_sell"),
                    )
                ),
                "price": float(execution.get("price") or 0),
                "commission": float(execution.get("commission") or 0),
                "realized_pnl": float(execution.get("realized_pnl") or 0),
                "buy_sell": execution.get("buy_sell"),
                "normalized_buy_sell": normalized_side,
                "order_id": execution.get("order_id"),
                "perm_id": execution.get("perm_id"),
                "client_id": execution.get("client_id"),
                "asset_class": execution.get("sec_type"),
                "secType": execution.get("sec_type"),
                "exchange": execution.get("exchange"),
                "currency": execution.get("currency"),
                "source": "tws_live",
                "last_tws_update": execution.get("last_update"),
            }
            db.ibkr_trades.update_one(
                {"trade_id": exec_id},
                {"$set": {**execution, **trade_doc}},
                upsert=True,
            )
            upserted += 1

        self.logger.info("Upserted %s TWS execution(s) into ibkr_trades.", upserted)
        return upserted

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
            socket_probe = self._probe_socket()
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

            connected = self.is_connected()
            managed_accounts = list(getattr(app, "managed_accounts", [])) if app is not None else []
            last_error = getattr(app, "last_error", None) if app is not None else None
            last_status = getattr(app, "last_status", None) if app is not None else None
            last_account_value_update = getattr(app, "last_account_value_update", None) if app is not None else None
            handshake_attempted = self._has_handshake_evidence(app)
            handshake_error = (
                last_error
                if last_error is not None and int(last_error.get("error_code", 0)) == 504
                else None
            )

            if not self.enabled:
                connection_state = "disabled"
                diagnosis = "TWS feature flag disabled."
            elif IBAPI_IMPORT_ERROR is not None:
                connection_state = "unavailable"
                diagnosis = "ibapi is not installed in this runtime."
            elif connected:
                connection_state = "connected"
                diagnosis = "IBKR TWS API session connected."
            elif socket_probe["tcp_connectable"] and handshake_attempted:
                connection_state = "handshake_failed"
                if handshake_error and handshake_error.get("error"):
                    diagnosis = (
                        "TCP socket is reachable, but the IBKR API handshake did not complete. "
                        f"Last IBKR error: {handshake_error.get('error')}. "
                        "Verify TWS trusted-client / localhost-only API settings for this runtime."
                    )
                else:
                    diagnosis = (
                        "TCP socket is reachable, but the IBKR API handshake did not complete. "
                        "Verify TWS trusted-client / localhost-only API settings for this runtime."
                    )
            elif last_error:
                connection_state = "socket_unreachable"
                diagnosis = f"TWS connection failed: {last_error.get('error')}"
            else:
                connection_state = "disconnected"
                diagnosis = "TWS is configured but no active session has been established."

            return {
                "connected": connected,
                "host": self.host,
                "port": self.port,
                "client_id": self.client_id,
                "managed_accounts": managed_accounts,
                "next_valid_order_id": getattr(app, "next_valid_order_id", None) if app is not None else None,
                "connection_attempted_at": getattr(app, "connection_attempted_at", None) if app is not None else None,
                "connected_at": getattr(app, "connected_at", None) if app is not None else None,
                "last_callback_at": getattr(app, "last_callback_at", None) if app is not None else None,
                "position_snapshot_complete": getattr(app, "position_snapshot_complete", False) if app is not None else False,
                "last_position_update": last_position_update,
                "last_account_value_update": last_account_value_update,
                "last_execution_update": getattr(app, "last_execution_update", None) if app is not None else None,
                "last_error": last_error,
                "last_status": last_status,
                "handshake_attempted": handshake_attempted,
                "position_count": len(positions),
                "execution_count": len(getattr(app, "executions", {})) if app is not None else 0,
                "execution_snapshot_complete": getattr(app, "execution_snapshot_complete", False) if app is not None else False,
                "socket_connectable": socket_probe["tcp_connectable"],
                "socket_probe_error": socket_probe["error"],
                "socket_local_address": socket_probe["local_address"],
                "connection_state": connection_state,
                "diagnosis": diagnosis,
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
