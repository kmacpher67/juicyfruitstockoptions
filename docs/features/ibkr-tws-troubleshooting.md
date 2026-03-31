# IBKR TWS Troubleshooting

## Purpose

Use this runbook when Juicy Fruit shows TWS live data as unavailable, stale, or partially working.

## What "Working" Means

For Juicy Fruit, TWS is only healthy when all of these are true from the same runtime that serves FastAPI:

- raw TCP can reach the configured TWS socket
- the IBKR API handshake completes
- managed accounts and/or account updates arrive
- scheduler jobs persist fresh `source: "tws"` and `source: "tws_live"` documents
- `/api/portfolio/live-status` and `/api/trades/live-status` report the real backend state

Raw socket reachability by itself is not enough.

## Common Failure Modes

- `disabled`: `IBKR_TWS_ENABLED` is false in the backend runtime.
- `socket_unreachable`: the configured host or port cannot be opened.
- `handshake_failed`: the TCP socket opened, but TWS did not complete the IB API session. This is the most common Docker-to-host failure.
- `disconnected`: the runtime is enabled and can probe the socket, but no successful handshake or callback evidence exists yet.
- `connected`: TWS callbacks have been received and the backend has a real IB API session.

## Required TWS Settings

In TWS:

- Enable `API` -> `Settings` -> `Enable ActiveX and Socket Clients`
- Use the correct port for the runtime you are connecting to:
  - TWS live: `7496`
  - TWS paper: `7497`
  - IB Gateway live: `4001`
  - IB Gateway paper: `4002`
- If Juicy Fruit runs outside the TWS host process namespace, do not rely on `localhost only` unless that runtime is truly local to TWS.
- If needed, add the backend runtime origin to the TWS trusted client list.
- Leave `Read-Only API` enabled or disabled based on whether you only need data or intend to place orders. It does not fix handshake failures.

## Docker Trusted IP Configuration

**`127.0.0.1` alone is not sufficient when the backend runs in Docker.**

TWS runs on the host machine. When the `backend` container connects to TWS via `host.docker.internal` (which resolves to the host gateway via `extra_hosts: host.docker.internal:host-gateway` in docker-compose), the connection arrives at TWS from the **Docker bridge gateway IP**, not `127.0.0.1`.

### Find your Docker gateway IP

```bash
docker network inspect juicyfruitstockoptions_default \
  --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
```

Add that IP (typically `172.18.0.1` for a compose-managed network) to TWS → API Settings → Trusted IPs alongside `127.0.0.1`.

### Lock the gateway to a stable IP (recommended)

Docker can assign different gateway IPs across restarts or upgrades. Pin it in `docker-compose.yml`:

```yaml
networks:
  default:
    ipam:
      config:
        - subnet: 172.20.0.0/24
          gateway: 172.20.0.1
```

Then add only `172.20.0.1` and `127.0.0.1` to TWS trusted IPs — no surprises after Docker updates.

### Symptom when this is the cause

`raw-connect-test` succeeds (TCP port is open) but `connect-test` reports `handshake_failed`. TWS may also show a trusted-client warning or reject dialog in its API log.

## Verification Order

Run these in order from the same runtime as the backend:

```bash
python -m app.scripts.ibkr_tws_cli status --show-env
python -m app.scripts.ibkr_tws_cli raw-connect-test --force-enable
python -m app.scripts.ibkr_tws_cli connect-test --force-enable
python -m app.scripts.ibkr_tws_cli sync-nav --force-enable
python -m app.scripts.ibkr_tws_cli sync-positions --force-enable --snapshot-id manual_verify_YYYYMMDD
python -m app.scripts.ibkr_tws_cli executions --force-enable
python -m app.scripts.ibkr_tws_cli sync-executions --force-enable
```

Interpretation:

- `raw-connect-test` success means only that the TCP socket is reachable.
- `connect-test` success means the IB API handshake completed.
- If `connect-test` fails with `326 Unable to connect as the client id is already in use`, retry immediately with `--client-id <unique number>` before classifying the runtime as broken.
- `sync-nav` success means the backend runtime can persist a fresh `source: "tws"` NAV snapshot.
- `sync-positions` success means the backend runtime can persist a fresh `source: "tws"` holdings snapshot.
- `executions` should return normalized rows with:
  - `date_time` formatted like `YYYYMMDD HH:MM:SS`
  - `trade_date` formatted like `YYYYMMDD`
  - `buy_sell` preserved from IBKR (`BOT` / `SLD`) with a normalized side available for downstream logic
  - signed `quantity` once persisted into `ibkr_trades`
- `sync-executions` success means current-day `tws_live` trade rows can be upserted into Mongo from the same runtime as FastAPI.

If `raw-connect-test` succeeds but `connect-test` reports `handshake_failed`, focus on TWS trust and client-origin settings first.

## Trade-Specific Checks

Juicy Fruit `RT` trades mode depends on current-day `tws_live` execution rows being queryable as "today." The backend now normalizes TWS execution timestamps into:

- `date_time`: `YYYYMMDD HH:MM:SS`
- `trade_date`: `YYYYMMDD`

If you can see executions in TWS but the web app shows zero current-day live rows:

1. Run `python -m app.scripts.ibkr_tws_cli executions --force-enable`
2. Confirm returned executions have the normalized `trade_date`
3. Run `python -m app.scripts.ibkr_tws_cli sync-executions --force-enable` if you want an immediate manual upsert
4. Confirm `/api/trades/live-status` reports `today_live_trade_count > 0`

Use [`executions.txt`](/home/kenmac/personal/juicyfruitstockoptions/executions.txt) as a sanity fixture for what same-day trades should roughly resemble across multiple accounts.

## When the UI Looks Wrong Even Though Data Exists

Known symptoms that are not handshake failures:

- RT trades rows exist, but the Action column is wrong because the data is using `buy_sell` rather than quantity sign.
- RT trades rows exist, but Price or Comm appears blank because the UI is reading Flex-era fields instead of live `price` / `commission`.
- Historical views appear fine while RT is empty because only current-day `tws_live` rows are shown in RT mode.
- `?view=PORTFOLIO` rows show `$undefined`, `NaN%`, blank option descriptions, or wrong `STK` / `OPT` typing because the frontend grid is reading the wrong field names from TWS/live or merged holdings rows. Treat this as a portfolio row-schema / formatter bug, not a socket-handshake bug.

For the portfolio-grid case above, compare the actual holdings payload fields used for:

- price / market value / basis / unrealized PnL
- `% NAV` denominator and numerator inputs
- `secType` / `sec_type` / `asset_class`
- option description fields used to build the contract label

Reference: [`portfolio_tws_live_grid_regressions_20260331.md`](/home/kenmac/personal/juicyfruitstockoptions/docs/features/portfolio_tws_live_grid_regressions_20260331.md)

## When To Grab TWS Logs

Only collect TWS logs after the same-runtime checks above show a handshake or callback problem that is still unexplained.

Helpful cases for logs:

- `raw-connect-test` succeeds
- `connect-test` fails or stays `disconnected`
- TWS displays an API prompt, reject dialog, or trusted-client warning
- callbacks stop arriving after a previously healthy session

If you want to provide logs, grab the TWS API logs from the current failing session after setting TWS API logging to `Detail`, then copy over the relevant files from the TWS log directory. On Windows this is commonly under `C:\Jts`.

## Operator Notes

- Host-shell success does not prove Docker or another backend runtime can handshake.
- If TWS trust cannot be made reliable for the deployed runtime, prefer an explicit fallback path over a misleading live badge.
- For portfolio debugging, use `/api/portfolio/live-status`.
- For trade debugging, use `/api/trades/live-status` plus a direct `executions` CLI run.
