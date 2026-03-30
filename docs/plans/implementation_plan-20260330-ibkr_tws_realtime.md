# Implementation Plan: IBKR Real-Time Data Integration (TWS API)
**File**: `docs/plans/implementation_plan-20260330-ibkr_tws_realtime.md`

---

## Overview

**Goal**: Add real-time intraday portfolio state to Juicy Fruit by integrating the IBKR TWS API via persistent socket connection — without replacing the existing Flex Report pipeline.

**Problem statement**: Flex Reports provide end-of-day and post-fill data. The frontend currently shows stale positions (up to 24h old) between syncs. For the 1D NAV widget and live portfolio P&L display, we need positions and NAV updated within seconds/minutes during market hours.

**Approach**: Layer TWS API on top of Flex. TWS = intraday source of truth. Flex = historical/EOD source of truth.

---

## Pre-Implementation Checklist

- [ ] Active IBKR account credentials available for IB Gateway Docker setup
- [ ] Docker Compose environment running and tested
- [ ] `IBKR_TWS_ENABLED=false` feature flag set (safe default — no impact until explicitly enabled)
- [ ] Review `docs/learning/ibkr-realtime-data-integration.md` (required context)
- [ ] Decision: paper trading port (4002) for dev, live port (4001/7497) for prod?

---

## Scope — What This Plan Covers

✅ IB Gateway Docker service  
✅ `IBKRTWSService` Python singleton  
✅ Scheduler jobs (position sync, NAV snapshot)  
✅ Two new API endpoints (`/live-status`, `/nav/live`)  
✅ Frontend data freshness badge (NAVStats)  
✅ Unit tests  

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

---

## Definition of Done

- [ ] `docker-compose up` starts IB Gateway service without errors
- [ ] `IBKRTWSService` connects to gateway and populates positions within 5 seconds
- [ ] `ibkr_holdings` updates every 30s with `source: "tws"` when gateway is running
- [ ] `nav_history` gets intraday entries every 3 minutes
- [ ] `GET /api/portfolio/live-status` returns correct connection state
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

---

## Related Documents

- `docs/learning/ibkr-realtime-data-integration.md` — domain knowledge
- `docs/learning/ibkr-flex-report-dividends.md` — existing Flex setup
- `docs/features-requirements.md` — epic-001-infra-tws-001 through 006
- `ARCHITECTURE.md` — updated after implementation

---

*Plan created: 2026-03-30 | Trader Ken / Juicy Fruit*  
*Status: **PENDING APPROVAL** — Do not implement until Ken approves.*
