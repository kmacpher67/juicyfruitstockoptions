# Implementation Plan: IBKR Real-Time Data Integration (TWS API)
**File**: `docs/plans/implementation_plan-20260330-ibkr_tws_realtime.md`

---

## Overview

**Goal**: Add real-time intraday portfolio state to Juicy Fruit by integrating the IBKR TWS API via persistent socket connection — without replacing the existing Flex Report pipeline.

**Problem statement**: Flex Reports provide end-of-day and post-fill data. The frontend currently shows stale positions (up to 24h old) between syncs. For the 1D NAV widget and live portfolio P&L display, we need positions and NAV updated within seconds/minutes during market hours.

**Approach**: Layer TWS API on top of Flex. TWS = intraday source of truth. Flex = historical/EOD source of truth.

## Current Focus Update - 2026-03-31

This plan is now the selected task set for the active web-app issue: "IBKR real-time TWS integration is still not working in the web app."

Critical-path interpretation:

1. The first thing to prove is not frontend rendering but backend-runtime handshake success.
2. The next thing to prove is scheduler persistence into Mongo from that same runtime.
3. Only after that should the UI be considered broken.

Selected tasks for the current fix:

- `ibkr-tws-webapp-fix-001`
- `ibkr-tws-webapp-fix-002`
- `ibkr-tws-webapp-fix-003`
- `ibkr-tws-webapp-fix-004`
- `ibkr-tws-logging-004`
- `ibkr-tws-logging-007`
- `ibkr-tws-reliability-001`
- `ibkr-tws-reliability-004`
- `ibkr-tws-reliability-005`

## Repeatable UI Roadmap - 2026-03-31

The feature request "IBKR Real-Time UI" is too large to repeat safely as one checklist line. Treat it as the following repeatable sequence:

1. Runtime truth first.
   Verify TWS connectivity from the same runtime as FastAPI using `app/scripts/ibkr_tws_cli.py` and `/api/portfolio/live-status`.
2. Persistence second.
   Confirm fresh intraday documents exist in Mongo before touching the UI:
   `nav_history` with `source: "tws"`, `ibkr_holdings` with `source: "tws"`, and later `ibkr_trades` with `source: "tws_live"`.
3. Contract third.
   Make `data_source`, `last_updated`, `connection_state`, and `diagnosis` the stable frontend contract so UI work is driven by backend truth.
4. `PORTFOLIO` intraday UX fourth.
   Add the RT/intraday time-series view, distinguish RT vs `1D`, and show a deliberate unavailable state instead of empty/zero pretending to be live.
5. `TRADES` intraday UX fifth.
   Only add live/current-day trade visuals after TWS execution sync, persistence, and an explicit API endpoint are in place.
6. End-to-end verification last.
   Re-check CLI -> API -> DB -> frontend for both `?view=PORTFOLIO` and `?view=TRADES`.

Follow-on feature IDs for this roadmap:

- `ibkr-tws-ui-rt-003`
- `ibkr-tws-ui-rt-004`
- `ibkr-tws-ui-rt-005`
- `ibkr-tws-ui-rt-006`

---

## Pre-Implementation Checklist

- [ ] Active IBKR account credentials available for IB Gateway Docker setup
- [ ] Docker Compose environment running and tested
- [ ] `IBKR_TWS_ENABLED=false` feature flag set (safe default — no impact until explicitly enabled)
- [ ] Review `docs/learning/ibkr-realtime-data-integration.md` (required context)
- [ ] Decision: paper trading port (4002) for dev, live port (4001/7497) for prod?
- [ ] Decision: local-host-only TWS or Docker-to-host TWS path, with trusted client behavior explicitly verified

---

## Scope — What This Plan Covers

✅ IB Gateway Docker service  
✅ `IBKRTWSService` Python singleton  
✅ Scheduler jobs (position sync, NAV snapshot)  
✅ Two new API endpoints (`/live-status`, `/nav/live`)  
✅ Frontend data freshness badge (NAVStats)  
✅ Unit tests  
✅ Runtime diagnostics for "socket reachable but IB API handshake failed"  

❌ Out of scope: Order placement, options chain streaming, Client Portal REST fallback (tracked separately as epic-001-infra-tws-006)

---

## Architecture After This Plan

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                         │
│  ┌──────────────┐    socket:4002    ┌────────────────┐  │
│  │  IB Gateway  │◄──────────────────│ ibkr_tws_      │  │
│  │  (headless)  │                   │ service.py     │  │
│  └──────────────┘                   └───────┬────────┘  │
│                                             │            │
│  ┌──────────────┐  reqPositions()           │            │
│  │  Scheduler   │──────────────────────────►│            │
│  │  (30s jobs)  │                           │ upsert     │
│  └──────────────┘                           ▼            │
│                                    ┌────────────────┐    │
│  ┌──────────────┐  REST            │   MongoDB      │    │
│  │  FastAPI     │◄─────────────────│ ibkr_holdings  │    │
│  │  routes.py   │                  │ nav_history    │    │
│  └──────┬───────┘                  └────────────────┘    │
│         │                                                 │
└─────────┼───────────────────────────────────────────────┘
          │ JSON
    ┌─────▼──────┐
    │  React     │
    │  NAVStats  │ ← freshness badge
    │  Portfolio │
    └────────────┘
```

---

## Implementation Order

Tasks are ordered by dependency. Tasks within the same phase can be parallelized by separate agents.

---

### Phase 1 — Infrastructure (Prerequisite for all other phases)

#### Task 1.1 — IB Gateway Docker Service
**File**: `docker-compose.yml`, `.env`, `ibgateway-config/`  
**Agent**: Can run standalone  
**Effort**: ~1–2 hours  

```yaml
# docker-compose.yml addition:
  ib-gateway:
    image: ghcr.io/waytrade/ib-gateway:latest
    restart: always
    environment:
      TWS_USERID: ${IBKR_USERNAME}
      TWS_PASSWORD: ${IBKR_PASSWORD}
      TRADING_MODE: ${IBKR_TRADING_MODE:-paper}
      TWS_SETTINGS_PATH: /home/ibgateway/Jts
    ports:
      - "${IBKR_TWS_PORT:-4002}:4002"
    volumes:
      - ./ibgateway-config:/home/ibgateway/Jts
    networks:
      - app-network
```

```bash
# .env additions:
IBKR_USERNAME=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password
IBKR_TRADING_MODE=paper          # paper | live
IBKR_TWS_HOST=ib-gateway         # Docker service name
IBKR_TWS_PORT=4002
IBKR_TWS_CLIENT_ID=1
IBKR_TWS_ENABLED=false           # Set true after gateway confirmed working
```

```python
# app/config.py additions (Pydantic BaseSettings):
ibkr_tws_host: str = "127.0.0.1"
ibkr_tws_port: int = 4002
ibkr_tws_client_id: int = 1
ibkr_tws_enabled: bool = False
```

**Verification**: `docker-compose up ib-gateway` → check logs for "IB Gateway started"

---

#### Task 1.2 — Install ibapi dependency
**File**: `requirements.txt`  
**Agent**: Can run standalone  
**Effort**: 15 min  

```
ibapi>=10.19.1
```

Verify: `pip install ibapi && python -c "from ibapi.client import EClient; print('OK')"`

---

### Phase 2 — Python Service (Depends on Phase 1)

#### Task 2.1 — Create `app/services/ibkr_tws_service.py`
**Effort**: ~2–3 hours  
**Single Responsibility**: Real-time position and account data from TWS socket  

Full implementation (see `docs/learning/ibkr-realtime-data-integration.md` Section 4 for code template):

Key methods to implement:
- `IBKRTWSApp(EWrapper, EClient)` — callbacks: `position`, `positionEnd`, `updateAccountValue`, `error`, `connectAck`
- `IBKRTWSService` — `connect()`, `disconnect()`, `get_positions()`, `get_account_values(account)`, `is_connected()`
- All logs follow: `{datetime} - ibkr_tws_service-{ClassName}.{method} - {LEVEL} - {message}`
- Graceful degradation: if `settings.ibkr_tws_enabled is False`, all methods return empty structures without error

Diagnostics requirements to add while implementing:
- Log raw TCP reachability separately from handshake success so operators can distinguish an open port from a live IB API session.
- Treat `2104`, `2106`, and `2158` as informational health callbacks, not hard errors.
- Preserve and expose `last_error` for true failures such as `504 Not connected`.
- Emit a compact live-status snapshot after connect attempts and before scheduler skips: `host`, `port`, `client_id`, `connected`, `managed_accounts`, `position_count`, `last_account_value_update`, `last_error`.

#### Task 2.1A — Add reconnect and handshake diagnostics
**Effort**: ~1–2 hours  
**Depends on**: Task 2.1

- Add bounded reconnect/backoff logic after disconnect or failed warmup handshake.
- Add a warmup timeout that logs a precise failure when the service can open a socket but never reaches `nextValidId`, `managedAccounts`, positions, or account values.
- Add an internal diagnostic helper path that makes the following state explicit:
  - socket reachable
  - IB API handshake complete
  - live data callbacks flowing

#### Task 2.2 — Register singleton in `app/main.py`
**Effort**: 30 min  
**Depends on**: Task 2.1  

```python
# app/main.py — FastAPI lifespan pattern
from contextlib import asynccontextmanager
from app.services.ibkr_tws_service import IBKRTWSService
from app.config import settings

tws_service: IBKRTWSService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tws_service
    if settings.ibkr_tws_enabled:
        tws_service = IBKRTWSService(settings.ibkr_tws_host, settings.ibkr_tws_port, settings.ibkr_tws_client_id)
        tws_service.connect()
    yield
    if tws_service:
        tws_service.disconnect()
```

---

### Phase 3 — Scheduler Jobs (Depends on Phase 2)

#### Task 3.1 — Add position sync job
**File**: `app/scheduler/jobs.py`  
**Effort**: 1–2 hours  
**Depends on**: Task 2.1, Task 2.2  

```python
async def run_tws_position_sync():
    """Sync live TWS positions to ibkr_holdings. Runs every 30s during market hours."""
    if not settings.ibkr_tws_enabled or not tws_service:
        return
    positions = tws_service.get_positions()
    # Upsert each position to ibkr_holdings with source="tws", last_tws_update=now
    # Key: (account, symbol, sec_type)
    # Do NOT overwrite flex fields (cost_basis, trade_history) — merge by key

async def run_tws_nav_snapshot():
    """Append NAV snapshot from TWS to nav_history. Runs every 3 min."""
    if not settings.ibkr_tws_enabled or not tws_service:
        return
    for account in settings.ibkr_accounts:  # list of account IDs
        values = tws_service.get_account_values(account)
        # Append to nav_history: {account, nav, unrealized_pnl, realized_pnl, source: "tws", timestamp: now}
```

Scheduler registration:
```python
scheduler.add_job(run_tws_position_sync, 'interval', seconds=30, id='tws_position_sync')
scheduler.add_job(run_tws_nav_snapshot, 'interval', seconds=180, id='tws_nav_snapshot')
```

Operational logging requirement:
- When jobs skip, log the specific reason with the current live-status snapshot rather than only "TWS is not connected".
- This is required for the observed failure mode where the backend has `IBKR_TWS_ENABLED=true` and TCP reachability, but no completed IB API handshake and therefore no persisted `source: "tws"` records.

---

### Phase 4 — API Endpoints (Depends on Phase 3)

#### Task 4.1 — Add `GET /api/portfolio/live-status`
**File**: `app/api/routes.py`  
**Effort**: 30 min  

```python
@router.get("/portfolio/live-status")
async def get_live_status():
    return {
        "tws_enabled": settings.ibkr_tws_enabled,
        "connected": tws_service.is_connected() if tws_service else False,
        "position_count": len(tws_service.get_positions()) if tws_service else 0,
        "last_position_update": tws_service.last_position_update if tws_service else None,
    }
```

Current expectation for the web app:
- this endpoint is the source of truth for live state
- the payload must keep `connection_state`, `diagnosis`, `socket_connectable`, `last_error`, `managed_accounts`, and `last_account_value_update`
- the frontend should not collapse all non-connected states into one generic fallback label

#### Task 4.2 — Update `GET /api/portfolio/stats` data source tagging
**File**: `app/api/routes.py`  
**Effort**: 30 min  

Add `data_source` and `last_updated` fields to existing response. Query `ibkr_holdings` for most recent `last_tws_update` timestamp. If within 60s → `data_source: "tws_live"`, else → `data_source: "flex_eod"`.

---

### Phase 5 — Frontend (Depends on Phase 4, can parallelize with Phase 3)

#### Task 5.1 — Data freshness badge in `NAVStats.jsx`
**Effort**: 1 hour  
**Depends on**: Task 4.1  

- Poll `GET /api/portfolio/live-status` every 60s
- Green dot badge: `connected: true` → "Live" 
- Yellow dot: `connected: false` but `data_source: "flex_eod"` → "EOD"
- Grey dot: `tws_enabled: false` → "Flex Only"
- Show `last_updated` as relative time: "updated 12s ago"
- This fixes the **1D NAV showing 0 bug** — the nav_history will have intraday entries from TWS

#### Task 5.1A — Replace generic "not working" UI state with diagnostic state
**Effort**: 30–60 min  
**Depends on**: Task 4.1

- Show `connection_state` and short `diagnosis` text in the live-status area
- Distinguish:
  - `disabled`
  - `disconnected`
  - `socket_unreachable`
  - `handshake_failed`
  - `connected`
- For `handshake_failed`, explicitly hint that the backend runtime can reach the socket but the IB API session did not complete
- Keep current NAV visible when falling back so the UI is informative, not blank

---

### Phase 6 — Tests

#### Task 6.1 — `tests/test_ibkr_tws_service.py`
**Effort**: 1–2 hours  
**Parallel**: Can run alongside Phase 2  

Test cases:
```python
def test_tws_disabled_returns_empty():
    """When IBKR_TWS_ENABLED=false, get_positions() returns {} without error."""

def test_position_callback_stored():
    """IBKRTWSApp.position() correctly stores to self.positions dict."""

def test_account_value_callback_stored():
    """IBKRTWSApp.updateAccountValue() correctly stores to self.account_values."""

def test_error_callback_logs_not_raises():
    """IBKRTWSApp.error() logs but does not raise an exception."""

def test_connect_calls_reqpositions(mock_eclient):
    """IBKRTWSService.connect() calls reqPositions() after handshake."""

def test_socket_reachable_but_handshake_failed_status():
    """Service preserves useful diagnostics when raw reachability exists but IB API handshake fails."""

def test_scheduler_skip_logs_specific_reason():
    """Scheduler skip logs explain why no TWS persistence occurred."""
```

---

## Data Model Changes

### `ibkr_holdings` collection — new fields added (non-breaking):
```json
{
  "source": "tws | flex",
  "last_tws_update": "2026-03-30T14:23:11Z",
  "last_flex_update": "2026-03-29T20:00:00Z"
}
```

Expand response shape to include richer diagnostics when available:
- `managed_accounts`
- `last_account_value_update`
- `last_error`
- `connection_attempted_at`
- `connected_at`

This lets the frontend and operators distinguish:
- live and healthy
- disabled
- fallback/EOD only
- handshake failed after socket reachability

### `nav_history` collection — new field:
```json
{
  "source": "tws | flex | manual",
  "unrealized_pnl": -1234.56,
  "realized_pnl": 5678.90
}
```

No migrations required — additive fields only.

---

## Rollout Plan

1. **Dev**: Set `IBKR_TWS_ENABLED=false` (default). All existing behavior unchanged.
2. **Test with paper account**: Set `IBKR_TRADING_MODE=paper`, `IBKR_TWS_ENABLED=true`. Verify positions match IBKR paper account.
3. **Production**: Set `IBKR_TRADING_MODE=live`, `IBKR_TWS_ENABLED=true`. Monitor logs for 24h.

Before calling a rollout successful, verify from the same runtime as the API service:

```bash
docker exec stock_portal_backend python -m app.scripts.ibkr_tws_cli status --show-env
docker exec stock_portal_backend python -m app.scripts.ibkr_tws_cli raw-connect-test --host host.docker.internal --port 7496 --timeout 3
docker exec stock_portal_backend python -m app.scripts.ibkr_tws_cli connect-test --host host.docker.internal --port 7496 --timeout 3
docker exec stock_portal_backend python -c "from pymongo import MongoClient; from app.config import settings; db=MongoClient(settings.MONGO_URI).get_default_database('stock_analysis'); print(db.ibkr_nav_history.find_one({'source':'tws'}, sort=[('timestamp',-1)]))"
```

Interpretation:

- `raw-connect-test=true` and `connect-test=false` means the web app is blocked by handshake/runtime trust, not by React rendering
- no recent `source: "tws"` docs means scheduler persistence is still not working
- once both handshake and persistence work, the remaining issue is genuinely frontend-specific

---

## Definition of Done

- [ ] `docker-compose up` starts IB Gateway service without errors
- [ ] `IBKRTWSService` connects to gateway and populates positions within 5 seconds
- [ ] Raw socket reachability and IB API handshake success are reported separately in CLI/logs
- [ ] `ibkr_holdings` updates every 30s with `source: "tws"` when gateway is running
- [ ] `nav_history` gets intraday entries every 3 minutes
- [ ] `GET /api/portfolio/live-status` returns correct connection state
- [ ] `GET /api/portfolio/live-status` returns enough failure context to distinguish disabled vs disconnected vs handshake failure
- [ ] NAVStats shows diagnostic live state instead of a generic broken/fallback state
- [ ] NAVStats badge shows green "Live" dot when connected
- [ ] **1D NAV widget no longer shows 0** (has intraday data points)
- [ ] All 5 unit tests pass (`pytest tests/test_ibkr_tws_service.py`)
- [ ] `IBKR_TWS_ENABLED=false` (default) causes zero behavior change for existing features
- [ ] `features-requirements.md` items marked `[x]` for completed tasks
- [ ] `docs/features/ibkr_tws_realtime.md` feature doc created

---

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| IB Gateway Docker image not maintained | Pin image tag, not `latest`. Test monthly. |
| TWS connection drops mid-session | `reconnect()` method with exponential backoff in `IBKRTWSService` |
| Client ID conflict (multiple app instances) | Use unique `IBKR_TWS_CLIENT_ID` per instance; document in README |
| IBKR session timeout overnight | IB Gateway handles re-auth; gateway config `auto-restart: true` |
| Paper vs live port confusion | Enforce via `IBKR_TRADING_MODE` env var, validate in `config.py` |
| Socket reachable but backend handshake fails | Verify from backend runtime, not host shell; document trusted-client / localhost-only TWS behavior |

---

## Related Documents

- `docs/learning/ibkr-realtime-data-integration.md` — domain knowledge
- `docs/learning/ibkr-flex-report-dividends.md` — existing Flex setup
- `docs/features-requirements.md` — epic-001-infra-tws-001 through 006
- `ARCHITECTURE.md` — updated after implementation

---

*Plan created: 2026-03-30 | Trader Ken / Juicy Fruit*  
*Status: **PENDING APPROVAL** — Do not implement until Ken approves.*
