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

## Selected Fix Tasks

These are the existing tasks selected to fix the current "still not working in the web app" problem:

1. `ibkr-tws-webapp-fix-001`: verify realtime from the same runtime as the API service.
2. `ibkr-tws-webapp-fix-002`: make `/api/portfolio/live-status` the source of truth for UI state.
3. `ibkr-tws-webapp-fix-003`: surface `connection_state`, `diagnosis`, and backend failure reason in the web app.
4. `ibkr-tws-webapp-fix-004`: confirm handshake -> scheduler persistence -> live NAV API -> NAVStats path end to end.
5. `ibkr-tws-logging-004` and `ibkr-tws-logging-007`: explain why persistence is not happening and pass that reason through to the UI.
6. `ibkr-tws-reliability-001` and `ibkr-tws-reliability-004`: add reconnect and startup failure behavior so a bad session does not silently stay dead.
7. `ibkr-tws-webapp-fix-005`: if TWS runtime trust cannot be made reliable, route the UI to the existing Client Portal fallback intentionally.

## Acceptance Criteria

- The backend can distinguish `disabled`, `disconnected`, `socket_unreachable`, `handshake_failed`, and `connected`.
- The frontend shows that specific state and diagnosis instead of a generic broken-live indicator.
- Operators can verify the exact failure from the backend runtime with the documented CLI steps.
- When handshake succeeds, recent `source: "tws"` documents appear in holdings/NAV collections and the web app shows intraday freshness.
- If handshake cannot succeed from the deployed runtime, the docs and UI make the fallback path explicit.

## Related Docs

- `docs/features-requirements.md`
- `docs/plans/implementation_plan-20260330-ibkr_tws_realtime.md`
- `docs/learning/ibkr-realtime-data-integration.md`
- `docs/features/ibkr-client-portal-fallback.md`
