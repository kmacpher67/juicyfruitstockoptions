import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from importlib.util import find_spec

from pymongo import MongoClient

from app.config import settings
from app.services.ibkr_tws_service import IBKRTWSService


def _build_runtime_context(
    service: IBKRTWSService,
    *,
    include_all_env: bool = False,
) -> dict[str, object]:
    tracked_env_keys = [
        "IBKR_TWS_ENABLED",
        "IBKR_TWS_HOST",
        "IBKR_TWS_PORT",
        "IBKR_TWS_CLIENT_ID",
        "IBKR_PORTAL_ENABLED",
        "IBKR_PORTAL_BASE_URL",
        "IBKR_PORTAL_ACCOUNT_ID",
        "VIRTUAL_ENV",
        "PYTHONPATH",
    ]
    env_snapshot = {
        key: os.environ.get(key)
        for key in tracked_env_keys
        if os.environ.get(key) is not None
    }
    if include_all_env:
        env_snapshot = dict(sorted(os.environ.items()))

    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "ibapi_importable": find_spec("ibapi") is not None,
        },
        "settings": {
            "IBKR_TWS_ENABLED": settings.IBKR_TWS_ENABLED,
            "IBKR_TWS_HOST": settings.IBKR_TWS_HOST,
            "IBKR_TWS_PORT": settings.IBKR_TWS_PORT,
            "IBKR_TWS_CLIENT_ID": settings.IBKR_TWS_CLIENT_ID,
        },
        "effective": {
            "enabled": service.enabled,
            "host": service.host,
            "port": service.port,
            "client_id": service.client_id,
        },
        "environment": env_snapshot,
    }


def _raw_connect_test(host: str, port: int, timeout_seconds: float) -> dict[str, object]:
    payload: dict[str, object] = {
        "host": host,
        "port": port,
        "timeout_seconds": timeout_seconds,
        "tcp_connectable": False,
    }

    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            payload["tcp_connectable"] = True
    except OSError as exc:
        payload["error_type"] = type(exc).__name__
        payload["error"] = str(exc)

    return payload


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client.get_default_database("stock_analysis")


def _upsert_positions(service: IBKRTWSService, *, snapshot_id: str | None = None) -> dict[str, object]:
    positions = service.get_positions()
    now = _utc_now()
    effective_snapshot_id = snapshot_id or f"manual_tws_{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    report_date = now.strftime("%Y-%m-%d")
    db = _get_db()
    upserted = 0

    for position in positions:
        account_id = position.get("account") or position.get("account_id")
        symbol = position.get("symbol")
        sec_type = position.get("sec_type") or position.get("secType") or "UNKNOWN"
        if not account_id or not symbol:
            continue

        doc = dict(position)
        doc.update(
            {
                "account_id": account_id,
                "date": now,
                "report_date": report_date,
                "snapshot_id": effective_snapshot_id,
                "quantity": position.get("position", 0),
                "secType": sec_type,
                "source": "tws",
                "last_tws_update": now,
            }
        )
        db.ibkr_holdings.update_one(
            {
                "snapshot_id": effective_snapshot_id,
                "account_id": account_id,
                "symbol": symbol,
                "secType": sec_type,
                "source": "tws",
            },
            {"$set": doc},
            upsert=True,
        )
        upserted += 1

    return {
        "requested": True,
        "snapshot_id": effective_snapshot_id,
        "position_count": len(positions),
        "upserted": upserted,
        "positions": positions,
    }


def _insert_nav_snapshots(service: IBKRTWSService, *, account: str | None = None) -> dict[str, object]:
    db = _get_db()
    now = _utc_now()
    report_date = now.strftime("%Y-%m-%d")
    live_status = service.get_live_status()
    accounts = [account] if account else list(live_status.get("managed_accounts") or [])
    if not accounts:
        accounts = sorted(
            {
                position.get("account")
                for position in service.get_positions()
                if position.get("account")
            }
        )

    inserted = []
    for account_id in accounts:
        values = service.get_account_values(account_id)
        if not values:
            continue

        def _float_value(key: str) -> float:
            payload = values.get(key) or {}
            try:
                return float(payload.get("value") or 0)
            except (TypeError, ValueError):
                return 0.0

        nav = _float_value("NetLiquidation")
        doc = {
            "account_id": account_id,
            "_report_date": report_date,
            "timestamp": now,
            "source": "tws",
            "ending_value": nav,
            "total_nav": nav,
            "unrealized_pnl": _float_value("UnrealizedPnL"),
            "realized_pnl": _float_value("RealizedPnL"),
            "last_tws_update": now,
        }
        db.ibkr_nav_history.insert_one(doc)
        inserted.append(doc)

    return {
        "requested": True,
        "account": account,
        "inserted_count": len(inserted),
        "snapshots": inserted,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or manually test the IBKR TWS real-time service."
    )
    parser.add_argument(
        "command",
        choices=[
            "status",
            "connect-test",
            "raw-connect-test",
            "positions",
            "sync-positions",
            "account-values",
            "sync-nav",
            "executions",
            "execution-diagnostics",
            "sync-executions",
        ],
        help="TWS action to run.",
    )
    parser.add_argument("--host", help="Override the TWS / IB Gateway host.")
    parser.add_argument("--port", type=int, help="Override the TWS / IB Gateway port.")
    parser.add_argument(
        "--client-id",
        type=int,
        help="Override the client id used for the TWS API session.",
    )
    parser.add_argument(
        "--account",
        help="Account id to use for account-values.",
    )
    parser.add_argument(
        "--force-enable",
        action="store_true",
        help="Run even when IBKR_TWS_ENABLED is false.",
    )
    parser.add_argument(
        "--show-env",
        action="store_true",
        help="Include relevant environment variables and effective settings in output.",
    )
    parser.add_argument(
        "--show-all-env",
        action="store_true",
        help="Include the full process environment in output.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Timeout in seconds for raw TCP socket checks.",
    )
    parser.add_argument(
        "--snapshot-id",
        help="Optional deterministic snapshot id for sync-positions upserts.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = IBKRTWSService(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        enabled=True if args.force_enable else None,
    )

    if args.command == "status":
        payload = service.get_live_status()
    elif args.command == "raw-connect-test":
        payload = _raw_connect_test(service.host, service.port, args.timeout)
    else:
        connect_result = service.connect()
        try:
            if args.command == "connect-test":
                payload = {
                    "connect_returned": connect_result,
                    **service.get_live_status(),
                }
            elif args.command == "positions":
                payload = service.get_positions()
            elif args.command == "sync-positions":
                payload = _upsert_positions(service, snapshot_id=args.snapshot_id)
            elif args.command == "executions":
                service.refresh_executions(account=args.account)
                payload = service.get_executions(account=args.account)
            elif args.command == "execution-diagnostics":
                service.refresh_executions(account=args.account)
                payload = service.get_execution_diagnostics(account=args.account)
            elif args.command == "sync-nav":
                payload = _insert_nav_snapshots(service, account=args.account)
            elif args.command == "sync-executions":
                service.refresh_executions(account=args.account)
                payload = {
                    "requested": True,
                    "account": args.account,
                    "upserted": service.upsert_executions_to_db(account=args.account),
                    "execution_count": len(service.get_executions(account=args.account)),
                }
            else:
                payload = service.get_account_values(args.account or "")
        finally:
            service.disconnect()

    if args.show_env or args.show_all_env:
        if isinstance(payload, dict):
            payload["debug"] = _build_runtime_context(
                service,
                include_all_env=args.show_all_env,
            )
        else:
            payload = {
                "result": payload,
                "debug": _build_runtime_context(
                    service,
                    include_all_env=args.show_all_env,
                ),
            }

    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
