# features-requirements.md — IBKR Real-Time Data Integration
# PASTE these entries into docs/features-requirements.md
# Location: Section 2 "Infrastructure & Modernization" → under "### Data Reliability"
# Insert after the existing "Mongo Backup Automation" block and before "TWS API container"
# (replaces/expands the existing sparse "TWS API container" stub)

---

### Data Reliability

- [ ] **IBKR Real-Time Data — IB Gateway Docker Container**: Add IB Gateway as a Docker Compose service for a persistent headless IBKR socket connection. Prerequisite for all TWS real-time tasks below.
    - [ ] **ibkr-tws-gateway-001**: Research and select IB Gateway Docker image (`waytrade/ib-gateway` vs `mvberg`). Validate paper port (4002) and live port (4001). Document in `docs/learning/ibkr-realtime-data-integration.md`.
    - [ ] **ibkr-tws-gateway-002**: Add `ib-gateway` service to `docker-compose.yml` with env vars `TWS_USERID`, `TWS_PASSWORD`, `TRADING_MODE`. Map port 4002. Add VNC port 5900 for dev debugging only.
    - [ ] **ibkr-tws-gateway-003**: Add new env vars to `.env` and `app/config.py` (Pydantic settings): `IBKR_TWS_HOST`, `IBKR_TWS_PORT`, `IBKR_TWS_CLIENT_ID`, `IBKR_TWS_ENABLED` (feature flag, default `false`). Zero disruption to existing Flex pipeline when flag is off.
    - [ ] **ibkr-tws-gateway-004**: Create `ibgateway-config/` directory at workspace root for IB Gateway settings persistence (volume mount). Add to `.gitignore`. Document setup steps in README.

- [ ] **IBKR Real-Time Data — TWS API Python Service**: Create `app/services/ibkr_tws_service.py` — a thread-safe singleton wrapping `ibapi` for real-time position and account data. Supplements (does NOT replace) `ibkr_service.py` Flex pipeline.
    - [ ] **ibkr-tws-service-001**: Add `ibapi>=10.19` to `requirements.txt`. Verify compatibility with Dockerfile Python version.
    - [ ] **ibkr-tws-service-002**: Implement `IBKRTWSApp(EWrapper, EClient)` with callbacks: `position()`, `positionEnd()`, `updateAccountValue()`, `connectAck()`, `error()`. Follow logging standard: `{datetime} - {filename-class-method} - {LEVEL} - {message}`.
    - [ ] **ibkr-tws-service-003**: Implement `IBKRTWSService` wrapper with `connect()`, `disconnect()`, `get_positions()`, `get_account_values(account)`, `is_connected()`. Use `threading.Thread(daemon=True)` for socket loop. Graceful no-op when `IBKR_TWS_ENABLED=false`.
    - [ ] **ibkr-tws-service-004**: Register as singleton in `app/main.py` FastAPI lifespan. Connect on startup if `IBKR_TWS_ENABLED=true`, disconnect on shutdown.
    - [ ] **ibkr-tws-service-005**: Write unit tests `tests/test_ibkr_tws_service.py`. Mock `EClient`/`EWrapper`. Cover: connect, position callback, account value callback, error handling, graceful degradation when flag is off.

- [ ] **IBKR Real-Time Data — Scheduler Sync Jobs**: Add APScheduler jobs to sync live TWS positions and NAV snapshots into MongoDB on a continuous intraday basis.
    - [ ] **ibkr-tws-jobs-001**: Add `run_tws_position_sync()` to `app/scheduler/jobs.py`. Pull from `IBKRTWSService.get_positions()`, upsert `ibkr_holdings` with `source: "tws"` and `last_tws_update` timestamp. Guard with `IBKR_TWS_ENABLED` flag. Schedule every 30s.
    - [ ] **ibkr-tws-jobs-002**: Add `run_tws_nav_snapshot()` job. Pull account values (NetLiquidation, UnrealizedPnL, RealizedPnL) and append to `nav_history` with `source: "tws"`. Schedule every 3 min. **Fixes the 1D NAV showing 0 bug** — intraday data points will now exist.
    - [ ] **ibkr-tws-jobs-003**: Tag existing Flex sync documents with `source: "flex"` so consumers can distinguish data freshness. Flex = authoritative for history; TWS = authoritative for current intraday state. Non-breaking additive field.

- [ ] **IBKR Real-Time Data — API Endpoints**: Expose live connection status and data freshness to the frontend.
    - [ ] **ibkr-tws-api-001**: Add `GET /api/portfolio/live-status` → returns `{ connected, last_position_update, position_count, tws_enabled }`. Used by frontend health indicator.
    - [ ] **ibkr-tws-api-002**: Update `GET /api/portfolio/stats` to include `data_source` (`"tws_live"` or `"flex_eod"`) and `last_updated` timestamp. Frontend uses this to show data staleness.
    - [ ] **ibkr-tws-api-003**: Add `GET /api/portfolio/nav/live` returning the latest intraday NAV snapshot from `nav_history` with `source: "tws"` tag.

- [ ] **IBKR Real-Time Data — Frontend Freshness Indicator**: Show when portfolio data was last refreshed and whether live TWS is connected.
    - [ ] **ibkr-tws-ui-001**: Add status badge to `NAVStats.jsx` — green dot = TWS live, yellow = EOD only, grey = disabled. Show `last_updated` as relative time ("updated 12s ago").
    - [ ] **ibkr-tws-ui-002**: Poll `GET /api/portfolio/live-status` every 60s from `Dashboard.jsx`. Update badge state without full page reload.
    - [ ] **ibkr-tws-ui-003**: Toast notification if TWS drops from `connected: true` to `connected: false` mid-session.

- [ ] **IBKR Real-Time Data — Logging & Diagnostics**: Make TWS failures understandable in logs, CLI output, and the UI.
    - [ ] **ibkr-tws-logging-001**: Distinguish raw socket reachability from a real IB API handshake. A passing TCP check must not be presented as equivalent to a live TWS session.
    - [ ] **ibkr-tws-logging-002**: Reclassify routine IBKR status callbacks (`2104`, `2106`, `2158`) as informational health signals rather than hard errors.
    - [ ] **ibkr-tws-logging-003**: Include richer live-status diagnostics in logs/API: `managed_accounts`, `last_account_value_update`, `last_error`, `connection_attempted_at`, `connected_at`.
    - [ ] **ibkr-tws-logging-004**: Log specific scheduler skip reasons so operators can tell whether the issue is disabled flag, failed handshake, missing positions, or missing account values.
    - [ ] **ibkr-tws-logging-005**: Document and surface the localhost-vs-Docker failure mode where host CLI succeeds, container raw socket succeeds, but backend `connect-test` still fails with `504 Not connected`.

- [ ] **IBKR Real-Time Data — Connection Reliability**: Keep the backend from silently remaining disconnected after startup failure or session drop.
    - [ ] **ibkr-tws-reliability-001**: Add reconnect/backoff behavior to `IBKRTWSService`.
    - [ ] **ibkr-tws-reliability-002**: Add a repeatable backend-runtime verification path that runs both raw socket and handshake checks from the same environment as FastAPI.
    - [ ] **ibkr-tws-reliability-003**: Add startup diagnostics that fail loudly when `IBKR_TWS_ENABLED=true` but no successful handshake occurs within warmup timeout.

- [ ] **IBKR Real-Time Data — Client Portal REST API** `[!] Lower priority — fallback only if TWS socket is not viable.` See [IBKR Real-Time Data Integration](learning/ibkr-realtime-data-integration.md) for decision matrix.
    - [ ] **ibkr-portal-001**: Research Client Portal gateway Docker setup. Document session keepalive requirement (POST `/tickle` every 60s).
    - [ ] **ibkr-portal-002**: Create `app/services/ibkr_portal_service.py` with session-aware polling: `get_positions()`, `get_summary()`, `keepalive()`. Add `IBKR_PORTAL_ENABLED` feature flag.
    - [ ] **[!] BLOCKED — Needs Decision**: Client Portal requires `clientportal.gw` Java process. Confirm if Docker Compose setup is acceptable or if TWS path above is sufficient before starting this item.

---
# Also update Section 7 of features-requirements.md:
# Under "## 7. Agile & Project Governance" find the naming example line and replace with:
#
# CURRENT (remove):
#   **Naming**: Use hierarchical IDs (e.g., `epic-001-trading-001-task-001`).
#
# REPLACE WITH:
#   **Naming**: Use hierarchical keyword IDs scoped to the feature area
#   (e.g., `ibkr-tws-service-001`, `portfolio-nav-001`, `signals-kalman-001`).
#
# Also update the section headers:
# CURRENT: ## 2. Infrastructure & Modernization (Epic 1)
# REPLACE:  ## 2. Infrastructure & Modernization
#
# CURRENT: ## 3. Algorithmic Trading Engines (Epic 2)
# REPLACE:  ## 3. Algorithmic Trading Engines
#
# CURRENT: ## 4. Dashboard & UX Features (Epic 3)
# REPLACE:  ## 4. Dashboard & UX Features
#
# CURRENT: ## 5. Agentic AI & Intelligence (Epic 4)
# REPLACE:  ## 5. Agentic AI & Intelligence
#
# CURRENT: ## 6. Risk Management & Safety (Epic 5)
# REPLACE:  ## 6. Risk Management & Safety
#
# Add to Changelog table:
# | 2026-03-30 | **REMOVED** | "Epic N" labels from all section headers and task ID naming convention. Replaced with keyword-scoped IDs (e.g., ibkr-tws-service-001). |
# | 2026-03-30 | **ADDED** | IBKR Real-Time Data integration items under Section 2 → Data Reliability |
