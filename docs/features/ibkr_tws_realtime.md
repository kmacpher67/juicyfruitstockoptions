# IBKR TWS Realtime Web App

## Purpose

Track the real-time IBKR Trader Workstation integration that feeds the web app portfolio header, current NAV, freshness badge, and intraday holdings state without replacing the existing Flex-report pipeline.

## Problem Statement

The web app can show that realtime is "not working" even when parts of the backend path are healthy. The current failure we need to fix is not just "UI badge wrong"; it is an end-to-end runtime diagnosis problem:

- host-side CLI may connect to local TWS successfully
- backend runtime may still fail the IB API handshake
- scheduler jobs then skip live persistence
- `/api/portfolio/nav/live` stays empty/stale
- the frontend falls back to Flex/EOD state and appears broken

## Current State

Implemented already:

- `app/services/ibkr_tws_service.py` exposes connection diagnostics, live status, positions, account values, and execution capture.
- `app/api/routes.py` exposes `/api/portfolio/live-status` and `/api/portfolio/nav/live`.
- `frontend/src/components/NAVStats.jsx` shows TWS live vs EOD/disabled state.
- `tests/test_ibkr_tws_service.py` covers handshake-failed status behavior.

Still open:

- the UI does not yet clearly surface the backend `connection_state` and `diagnosis`
- reconnect and warmup failure behavior are still incomplete
- the Docker-to-host TWS trust/localhost requirement remains a likely blocker in the failing web-app path
- the realtime UI requirement for `PORTFOLIO` and `TRADES` is still too broad unless it is broken into repeatable implementation steps

## Data Source Rules

- TWS is the preferred source for intraday freshness, including current NAV, `1 Day`, and any explicit realtime/RT view.
- Flex remains the source of truth for historical and end-of-day reporting.
- The UI should never imply that realtime is active unless `/api/portfolio/live-status` says the runtime is truly connected.
- Unavailable is a first-class state. The UI should expose the backend diagnosis rather than silently falling back and looking broken.

## Repeatable FR Breakdown

Use this order whenever the "IBKR Real-Time UI" feature request is implemented or revisited:

1. Confirm the backend runtime can complete the IB API handshake from the same runtime that serves FastAPI.
2. Confirm scheduler persistence is writing fresh `source: "tws"` documents into `nav_history` and `ibkr_holdings`, and fresh `source: "tws_live"` execution documents into `ibkr_trades` once trade sync is enabled.
3. Expose a stable UI contract: `data_source`, `last_updated`, `connection_state`, and `diagnosis` must be available before changing visuals.
4. Implement `?view=PORTFOLIO` intraday UX first: current NAV, freshness badge, RT/`1D` distinction, and a deliberate unavailable state.
5. Implement `?view=TRADES` intraday UX second: current-day TWS executions, live-vs-Flex labeling, and duplicate-safe merge behavior once Flex catches up.
6. Verify the whole path end to end: CLI -> API -> Mongo collections -> frontend rendering.

## UI Scope

### `?view=PORTFOLIO`

- Show whether the current card is using `tws_live` intraday data or Flex/EOD fallback.
- Add an RT/intraday time-series path backed by `nav_history` documents tagged with `source: "tws"`.
- Treat `1D` as a live intraday view when a fresh TWS NAV snapshot exists; otherwise label it as fallback/EOD.
- If realtime is unavailable, show a clear state such as disabled, handshake failed, or disconnected instead of a misleading flat/zero chart.

### `?view=TRADES`

- Do not call the trades view realtime until current-day TWS execution sync is persisted and exposed via API.
- When enabled, label rows or summaries by source so users can tell `tws_live` intraday executions from later Flex history.
- Avoid duplicates when the same trade appears first from TWS and later from Flex.
- If live trades are unavailable, keep the historical trade view working and explain why realtime is absent.

## Selected Fix Tasks

These are the existing tasks selected to fix the current "still not working in the web app" problem:

1. `ibkr-tws-webapp-fix-001`: verify realtime from the same runtime as the API service.
2. `ibkr-tws-webapp-fix-002`: make `/api/portfolio/live-status` the source of truth for UI state.
3. `ibkr-tws-webapp-fix-003`: surface `connection_state`, `diagnosis`, and backend failure reason in the web app.
4. `ibkr-tws-webapp-fix-004`: confirm handshake -> scheduler persistence -> live NAV API -> NAVStats path end to end.
5. `ibkr-tws-logging-004` and `ibkr-tws-logging-007`: explain why persistence is not happening and pass that reason through to the UI.
6. `ibkr-tws-reliability-001` and `ibkr-tws-reliability-004`: add reconnect and startup failure behavior so a bad session does not silently stay dead.
7. `ibkr-tws-webapp-fix-005`: if TWS runtime trust cannot be made reliable, route the UI to the existing Client Portal fallback intentionally.
8. `ibkr-tws-ui-rt-003` through `ibkr-tws-ui-rt-006`: complete the repeatable RT UI roadmap for `PORTFOLIO` and `TRADES`.

## Acceptance Criteria

- The backend can distinguish `disabled`, `disconnected`, `socket_unreachable`, `handshake_failed`, and `connected`.
- The frontend shows that specific state and diagnosis instead of a generic broken-live indicator.
- Operators can verify the exact failure from the backend runtime with the documented CLI steps.
- When handshake succeeds, recent `source: "tws"` documents appear in holdings/NAV collections and the web app shows intraday freshness.
- The `PORTFOLIO` view can intentionally distinguish RT/intraday data from Flex/EOD fallback.
- The `TRADES` view does not claim realtime support until TWS execution sync, API exposure, and duplicate-safe rendering are all in place.
- If handshake cannot succeed from the deployed runtime, the docs and UI make the fallback path explicit.

## Related Docs

- `docs/features-requirements.md`
- `docs/plans/implementation_plan-20260330-ibkr_tws_realtime.md`
- `docs/learning/ibkr-realtime-data-integration.md`
- `docs/features/ibkr-client-portal-fallback.md`
