# Implementation Plan: Data Freshness & DB-First Architecture

Date: 2026-04-04

## Objective
Implement DB-first API behavior with asynchronous refresh, tiered freshness, and source precedence so frontend queries stay fast and data integrity remains explicit.

## Related F-R Items
- `data-freshness-db-first-001..003`
- `data-freshness-policy-001..005`
- `data-freshness-source-rule-001..002`
- `data-model-instrument-001..003`
- `data-ingest-scheduler-001..003`
- `data-freshness-tests-001..003`

## Phase 1: API Contract Foundation
- Add shared freshness evaluator and metadata shape in backend routes/services.
- Apply contract to high-traffic endpoints first (`ticker`, `opportunity`, `signals`, optimizer meta path).
- Add stale refresh queueing with cooldown to avoid duplicate enqueue bursts.
- Add focused regression tests for helper logic and route-level stale behavior.

Done status (current):
- Implemented for `ticker`, `opportunity`, `signals`.
- Added optimizer `include_meta=true` path.
- Added stale-refresh queue cooldown and route-level regression tests.

## Phase 2: Async Refresh Pipeline
- Replace direct `run_stock_live_comparison(..., trigger="sync")` queue calls with a dedicated refresh queue service.
- Add per-symbol dedupe + retry/backoff + failure telemetry.
- Persist refresh queue events for observability and operator diagnostics.

## Phase 3: Data Model Split (Snapshot + History)
- Keep lightweight latest instrument snapshot for fast reads.
- Add append-only instrument price history collection for charting/audit.
- Define and apply indexes:
  - `(instrument_key, timestamp desc)`
  - `(source, timestamp desc)`
- Add retention/rollup policy for long-range history management.

## Phase 4: Scheduler & Source Precedence
- Implement scheduler-sharded ingestion windows (avoid burst polling).
- Enforce source precedence by field type:
  - intraday price-sensitive -> TWS preferred when connected,
  - historical/EOD -> Flex authoritative,
  - fallback/backfill -> yfinance/Flex.
- Capture ingest telemetry per run (updated rows, stale-hit ratio, source, failures).

## Phase 5: Full Endpoint Coverage
- Apply DB-first metadata contract to remaining analysis and portfolio-support endpoints.
- Ensure no request-time blocking external fetches for normal UI queries.
- Add API-level regression tests covering stale paths, fallback source order, and metadata consistency.

## Phase 6: Frontend Contract Adoption
- Update UI consumers to render freshness fields consistently.
- Add user-facing stale reason badges where required.
- Add frontend tests for DB-first fallback rendering and stale-state messaging.

## Exit Criteria
- Core data endpoints are DB-first by default.
- Stale data triggers async refresh rather than request blocking.
- Metadata contract is consistent across endpoints.
- Source precedence behavior is documented, tested, and observable.
