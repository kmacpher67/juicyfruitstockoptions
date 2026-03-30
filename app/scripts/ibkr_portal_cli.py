import argparse
import json

from app.services.ibkr_portal_service import IBKRPortalService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the IBKR Client Portal gateway fallback service."
    )
    parser.add_argument(
        "command",
        choices=["positions", "summary", "keepalive", "status"],
        help="Client Portal action to run.",
    )
    parser.add_argument(
        "--base-url",
        help="Override the Client Portal API base URL, e.g. https://localhost:5000/v1/api",
    )
    parser.add_argument(
        "--account-id",
        help="Override the IBKR account id used for positions/summary requests.",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="Verify the Client Portal TLS certificate.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--force-enable",
        action="store_true",
        help="Run even when IBKR_PORTAL_ENABLED is false.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = IBKRPortalService(
        base_url=args.base_url,
        enabled=True if args.force_enable else None,
        account_id=args.account_id,
        verify_ssl=args.verify_ssl,
        timeout_seconds=args.timeout,
    )

    if args.command == "positions":
        payload = service.get_positions()
    elif args.command == "summary":
        payload = service.get_summary()
    elif args.command == "keepalive":
        payload = service.keepalive()
    else:
        payload = {
            "enabled": service.enabled,
            "base_url": service.base_url,
            "account_id": service.account_id,
            "verify_ssl": service.verify_ssl,
            "timeout_seconds": service.timeout_seconds,
        }

    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
