import argparse
import json

from app.services.ibkr_tws_service import IBKRTWSService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or manually test the IBKR TWS real-time service."
    )
    parser.add_argument(
        "command",
        choices=["status", "connect-test", "positions", "account-values"],
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
        payload = {
            "enabled": service.enabled,
            "host": service.host,
            "port": service.port,
            "client_id": service.client_id,
            "connected": service.is_connected(),
        }
    else:
        service.connect()
        try:
            if args.command == "connect-test":
                payload = {
                    "enabled": service.enabled,
                    "connected": service.is_connected(),
                    "positions": len(service.get_positions()),
                }
            elif args.command == "positions":
                payload = service.get_positions()
            else:
                payload = service.get_account_values(args.account or "")
        finally:
            service.disconnect()

    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
