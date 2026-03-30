import argparse
import json
import os
import socket
import sys
from importlib.util import find_spec

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
            "account-values",
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
