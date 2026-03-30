# IBKR Real-Time Data Integration
**docs/learning/ibkr-realtime-data-integration.md**

> **Purpose**: Explains the three IBKR data mechanisms, why Flex alone is insufficient for intraday use,  
> and how to add TWS API or Client Portal REST to Juicy Fruit without replacing Flex Reports.

---

## 1. Etymology / First Principles

**IBKR** = Interactive Brokers. They expose portfolio data through three distinct channels, each designed for a different use case. Think of them like three pipes with different flow rates:

| Pipe | Protocol | Latency | Use Case |
|------|----------|---------|----------|
| **Activity Flex** | XML/CSV over HTTPS (pull) | End-of-day | Nightly snapshot, trade history |
| **Trade Confirms Flex** | XML over HTTPS (pull) | Near-instant post-fill | Post-trade confirmation |
| **TWS API** | Socket (persistent TCP) | ~250ms ticks, positions in seconds | Real-time portfolio state |
| **Client Portal REST** | HTTPS (poll) | Seconds | Custom dashboards, OAuth apps |

The **Flex Reports** (`ibkr_service.py`) already handle EOD and post-fill data. The gap is **intraday portfolio state** — positions, P&L, and prices updated in near real-time.

---

To download the Python API, you do not need to download it manually from the official website. The official IBKR Python SDK is distributed as a package named ibapi, which you can install via pip
. Simply add ibapi>=10.19 to your project's requirements.txt file and run pip install ibapi
https://ibkrcampus.com/campus/trading-course/python-tws-api/
The way docker is NOT used anymore: https://github.com/waytrade/ib-gateway-docker?tab=readme-ov-file


## 2. The Three Mechanisms — Deep Dive

### 2A. Activity Flex Query (Current — Juicy Fruit Uses This)
- **What**: Scheduled XML report exported from IBKR servers
- **When**: Runs once daily (or on-demand with a delay of ~5–15 min)
- **Latency**: End-of-day. Cannot give you current intraday positions.
- **Auth**: Flex Token (already in `.env` as `IBKR_FLEX_TOKEN`)
- **Current code**: `app/services/ibkr_service.py`
- **Do NOT replace** — it's the authoritative source for trade history, dividends, and EOD positions.

### 2B. TWS API (Recommended Addition — Real-Time)
- **What**: A persistent **TCP socket** connection to Trader Workstation (TWS) or IB Gateway running on your machine
- **When**: Always-on; data streams in continuously while connected
- **Latency**: 
  - Market data ticks: ~4x/sec within 250ms
  - Position updates: seconds after a fill
  - Account values (NAV, cash): refreshed every ~3 minutes
- **Auth**: No OAuth. TWS/Gateway must be running and configured to allow API connections from `127.0.0.1`
- **Library**: `ibapi` — the official IBKR Python SDK (`pip install ibapi`)
- **Key calls**:
  ```python
  app.reqAccountUpdates(True, accountCode)   # NAV, cash, margin
  app.reqPositions()                          # All positions across accounts
  app.reqMktData(reqId, contract, "", False, False, [])  # Live price ticks
  ```
- **Gotcha**: TWS/IB Gateway must stay running. For production use, IB Gateway (headless) is preferred over full TWS.

### 2C. Client Portal REST API (Alternative — Dashboard Friendly)
- **What**: Standard HTTPS REST API — no socket needed
- **When**: Polled on a schedule (e.g., every 30 seconds)
- **Latency**: Seconds per poll cycle
- **Auth**: OAuth 2.0 + session keepalive (requires a running local gateway process — `clientportal.gw`)
- **Key endpoints**:
  ```
  GET /v1/api/portfolio/{accountId}/positions/0   → positions
  GET /v1/api/portfolio/{accountId}/summary       → NAV, P&L
  GET /v1/api/iserver/account/pnl/partitioned     → real-time P&L
  ```
- **Gotcha**: Requires the `clientportal.gw` Java process running locally (separate from TWS). Session expires every ~24h and needs a re-auth ping.
- **Trade-off vs TWS API**: Easier to integrate (REST vs socket) but slightly higher latency and requires session management.

---

## 3. Recommendation for Juicy Fruit

### Don't replace Flex. Layer on top of it.

```
Flex Reports (existing)     → Trade history, dividends, EOD snapshot  ← KEEP
TWS API (add)               → Intraday positions, NAV, live prices     ← ADD
Client Portal (optional)    → Alternative if TWS socket is too complex ← CONSIDER
```

**Recommended path**: Add TWS API via `ibapi`. It's the most real-time, requires no OAuth setup, and works with the IB Gateway Docker container your team already researched (`mvberg/ib-gateway-docker`).

---

## 4. TWS API Setup — Step by Step

### Step 1: Install IB Gateway (headless, Docker-friendly)
```bash
# https://ibkrcampus.com/campus/trading-course/python-tws-api/ 
# Option A: IBC-based Docker container (recommended for server/Docker Compose)
# Reference: https://github.com/IbcAlpha/IBC
# Reference: https://github.com/waytrade/ib-gateway-docker

docker pull ghcr.io/waytrade/ib-gateway:latest

# docker-compose addition (see Section 6 below)
```

### Step 2: Configure IB Gateway to allow API connections
In IB Gateway UI (or config file):
- Enable **API** → check "Enable ActiveX and Socket Clients"
- Set **Socket port** based on client type:
- `4002` = IB Gateway paper
- `4001` = IB Gateway live
- `7497` = Trader Workstation paper
- `7496` = Trader Workstation live
- Allow connections from: `127.0.0.1` (or Docker network subnet)
- Disable "Read-Only API" if you want order placement later

### Step 3: Install Python library
```bash
pip install ibapi
# or via requirements.txt:
echo "ibapi==9.81.1.post1" >> requirements.txt
```

Note: as of March 30, 2026, PyPI exposes `ibapi==9.81.1.post1`, not `10.19+`. The local Juicy Fruit setup was verified with the PyPI package on Python 3.12.

### Step 4: Create `app/services/ibkr_tws_service.py`
```python
"""
ibkr_tws_service.py — Real-time IBKR data via TWS API socket connection.
Supplements (does NOT replace) ibkr_service.py Flex Report ingestion.
"""
import threading
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class IBKRTWSApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.positions = {}        # {(account, symbol): position_dict}
        self.account_values = {}   # {(account, key): value}
        self.connected = False

    def connectAck(self):
        self.connected = True
        logger.info("ibkr_tws_service - IBKRTWSApp.connectAck - INFO - TWS API connected")

    def position(self, account, contract, position, avgCost):
        key = (account, contract.symbol, contract.secType)
        self.positions[key] = {
            "account": account,
            "symbol": contract.symbol,
            "sec_type": contract.secType,
            "position": position,
            "avg_cost": avgCost,
            "last_update": time.time()
        }

    def positionEnd(self):
        logger.info(f"ibkr_tws_service - positionEnd - INFO - Received {len(self.positions)} positions")

    def updateAccountValue(self, key, val, currency, accountName):
        self.account_values[(accountName, key)] = {
            "value": val,
            "currency": currency,
            "last_update": time.time()
        }

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        logger.error(f"ibkr_tws_service - error - ERROR - reqId={reqId} code={errorCode} msg={errorString}")


class IBKRTWSService:
    """Service wrapper for TWS API real-time data. Thread-safe."""

    def __init__(self, host="127.0.0.1", port=4002, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.app = None
        self._thread = None

    def connect(self):
        self.app = IBKRTWSApp()
        self.app.connect(self.host, self.port, self.client_id)
        self._thread = threading.Thread(target=self.app.run, daemon=True)
        self._thread.start()
        time.sleep(1)  # Allow handshake
        self.app.reqPositions()
        logger.info(f"ibkr_tws_service - connect - INFO - Connected to {self.host}:{self.port}")

    def get_positions(self) -> dict:
        return dict(self.app.positions) if self.app else {}

    def get_account_values(self, account: str) -> dict:
        if not self.app:
            return {}
        return {k[1]: v for k, v in self.app.account_values.items() if k[0] == account}

    def disconnect(self):
        if self.app:
            self.app.disconnect()
            logger.info("ibkr_tws_service - disconnect - INFO - Disconnected from TWS")
```

### Step 5: Add environment variables to `.env`
```bash
# TWS / IB Gateway connection
IBKR_TWS_HOST=127.0.0.1
IBKR_TWS_PORT=7496          # live TWS desktop on localhost
IBKR_TWS_CLIENT_ID=1
IBKR_TWS_ENABLED=true       # Feature flag — enable when TWS is running locally
```

For IB Gateway, switch the port to `4002` for paper or `4001` for live.

### Step 5A: Interpreting the first successful live connection

Example local verification:

```bash
python -m app.scripts.ibkr_tws_cli connect-test --force-enable
```

Typical startup output may include:

- `2104`: market data farm connection is OK
- `2106`: HMDS data farm connection is OK
- `2158`: sec-def data farm connection is OK

These are informational IBKR status messages, not failures. A successful session will still report `"connected": true` even if the initial position count is `0`.

### Step 6: Docker Compose addition
```yaml
# Add to docker-compose.yml
services:
  ib-gateway:
    image: ghcr.io/waytrade/ib-gateway:latest
    restart: always
    environment:
      TWS_USERID: ${IBKR_USERNAME}
      TWS_PASSWORD: ${IBKR_PASSWORD}
      TRADING_MODE: paper   # or 'live'
      TWS_SETTINGS_PATH: /home/ibgateway/Jts
    ports:
      - "4002:4002"   # paper API port
      - "5900:5900"   # VNC (optional, for debugging)
    volumes:
      - ./ibgateway-config:/home/ibgateway/Jts
```

---

## 5. Client Portal REST API Setup (Alternative)

If Docker/socket complexity is undesirable, the Client Portal gateway is a REST-based option.
https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#download-java

Should I create a custom Dockerfile-ibkr-port or just a shell script likely need that for docker
put a script in there to curl download and unzip into clientportal.gw/ 
https://download2.interactivebrokers.com/portal/clientportal.gw.zip
& Update this section 

### Step 1: Download and run Client Portal Gateway
```bash
# Repo-local gateway bundle:
docker-compose up ibkr-portal

# Or run directly from the checked-in bundle:
cd clientportal.gw
./bin/run.sh root/conf.yaml

# Gateway listens on https://localhost:5000
```

### Step 2: Authenticate (one-time per session)
```bash
# Navigate browser to https://localhost:5000 and log in with IBKR credentials
# Session lasts ~24h; needs a keepalive ping
curl -X POST https://localhost:5000/v1/api/tickle
```

### Step 3: Python polling service
```python
"""ibkr_portal_service.py — Client Portal REST polling."""
import requests
import urllib3
urllib3.disable_warnings()  # Self-signed cert on localhost

BASE = "https://localhost:5000/v1/api"

def get_positions(account_id: str) -> list:
    r = requests.get(f"{BASE}/portfolio/{account_id}/positions/0", verify=False)
    return r.json()

def get_summary(account_id: str) -> dict:
    r = requests.get(f"{BASE}/portfolio/{account_id}/summary", verify=False)
    return r.json()
```

### Step 4: Juicy Fruit fallback settings
```bash
export IBKR_PORTAL_ENABLED=true
export IBKR_PORTAL_BASE_URL=https://localhost:5000/v1/api
export IBKR_PORTAL_ACCOUNT_ID=DU123456      # Optional; service can auto-discover via /portfolio/accounts
export IBKR_PORTAL_VERIFY_SSL=false         # Expected for the local self-signed cert
export IBKR_PORTAL_TIMEOUT_SECONDS=10
```

### Step 5: Manual verification CLI
```bash
python -m app.scripts.ibkr_portal_cli status
python -m app.scripts.ibkr_portal_cli keepalive --force-enable --base-url https://localhost:5000/v1/api
python -m app.scripts.ibkr_portal_cli positions --force-enable --account-id DU123456
python -m app.scripts.ibkr_portal_cli summary --force-enable --account-id DU123456
```

---

## 6. Integration with Existing Juicy Fruit Architecture

### Where TWS data fits in the data flow:
```
[IB Gateway Docker] ──socket──► [IBKRTWSService]
                                      │
                              reqPositions() every ~30s
                              reqAccountUpdates() continuous
                                      │
                              ┌───────▼────────┐
                              │  MongoDB       │
                              │  ibkr_holdings │  ← upsert live positions
                              │  nav_history   │  ← append NAV snapshots
                              └───────┬────────┘
                                      │
                              FastAPI endpoints
                              /portfolio/stats
                              /portfolio/positions
                                      │
                              React frontend
                              NAVStats.jsx
                              PortfolioGrid.jsx
```

### Scheduler job addition (`app/scheduler/jobs.py`):
```python
# Add alongside existing run_ibkr_sync
scheduler.add_job(
    run_tws_position_sync,
    'interval',
    seconds=30,
    id='tws_position_sync',
    replace_existing=True
)
```

---

## 7. Decision Matrix — TWS API vs Client Portal

| Factor | TWS API | Client Portal REST |
|--------|---------|-------------------|
| Latency | ~250ms ticks | ~5-30s polled |
| Setup complexity | Medium (socket + Docker) | High (Java gateway + OAuth session) |
| Requires running process | IB Gateway | clientportal.gw |
| Docker-friendly | ✅ Yes (`ib-gateway-docker`) | ⚠️ Harder to containerize |
| Production stability | ✅ Battle-tested | ⚠️ Session expiry issues |
| Order placement (future) | ✅ Yes | ✅ Yes |
| **Recommendation** | **✅ Use this** | Fallback only |

---

## 8. Security Considerations

- Never expose TWS API port (4002/7497) to the public internet — localhost/Docker network only
- Store `IBKR_USERNAME` and `IBKR_PASSWORD` in Docker Secrets or `.env` (never hardcode)
- Use `IBKR_TWS_ENABLED=false` feature flag so the service gracefully degrades when gateway is down
- Client ID must be unique per connection — conflicts cause disconnections

---

## 9. Known Limitations

- **TWS API**: IBKR limits concurrent connections; use a single shared `IBKRTWSService` singleton
- **Market data subscriptions**: Some real-time ticks require paid IBKR market data subscriptions
- **Paper vs Live ports**: Paper = 4002/7496, Live = 4001/7497 — must match your account type
- **Flex Reports remain authoritative** for trade history/dividends — TWS data is for intraday state only

---

## 10. References

- [IBKR TWS API Official Docs](https://interactivebrokers.github.io/tws-api/)
- [ibapi Python package](https://pypi.org/project/ibapi/)
- [IB Gateway Docker (waytrade)](https://github.com/waytrade/ib-gateway-docker)
- [IBC — IB Controller (headless TWS)](https://github.com/IbcAlpha/IBC)
- [Client Portal API Docs](https://interactivebrokers.github.io/cpwebapi/)
- Related learning docs: `ibkr-flex-report-dividends.md`, `greeks-data-ingestion.md`

---

*Last updated: 2026-03-30 | Author: Trader Ken / Juicy Fruit*
