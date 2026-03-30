# IBKR Client Portal Fallback

## Purpose

Provide a lower-priority IBKR real-time fallback when the TWS socket path is unavailable or not yet operational. This implementation is additive and does not replace the existing Flex ingestion flow.

## Delivered

- `docker-compose.yml` now includes an `ibkr-portal` service that runs the checked-in `clientportal.gw` bundle with `./bin/run.sh root/conf.yaml`.
- `app/config.py` now exposes:
  - `IBKR_PORTAL_ENABLED`
  - `IBKR_PORTAL_BASE_URL`
  - `IBKR_PORTAL_ACCOUNT_ID`
  - `IBKR_PORTAL_VERIFY_SSL`
  - `IBKR_PORTAL_TIMEOUT_SECONDS`
- `app/services/ibkr_portal_service.py` provides:
  - `keepalive()`
  - `get_positions()`
  - `get_summary()`
- `app/scripts/ibkr_portal_cli.py` provides a manual verification CLI for `status`, `keepalive`, `positions`, and `summary`.
- `tests/test_ibkr_portal_service.py` covers disabled-mode behavior, keepalive, account discovery, and summary fetching.

## Behavior

- The feature is off by default.
- When disabled, the service returns safe empty values instead of raising on missing gateway state.
- TLS verification defaults to `false` because the local Client Portal gateway commonly uses a self-signed certificate.
- If `IBKR_PORTAL_ACCOUNT_ID` is unset, the service attempts to discover it from `GET /portfolio/accounts`.

## Current Scope Boundary

- This work does not register the Client Portal service in FastAPI lifespan.
- This work does not add scheduler jobs or frontend status indicators.
- This work is intended for manual or future orchestrated fallback usage.

## Manual Use

```bash
docker-compose up ibkr-portal
python -m app.scripts.ibkr_portal_cli status
python -m app.scripts.ibkr_portal_cli keepalive --force-enable --base-url https://localhost:5000/v1/api
```
