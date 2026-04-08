# Juicys Navigation + Optimizer Workspace

> **Date:** 2026-04-07  
> **Status:** Implemented (Phase 1 complete)  
> **Parent Requirements:** `docs/features-requirements.md` (`juicys-nav-*`, `stock-analysis-optimizer-juicy-table-*`, `juicy-opportunity-refresh-job-*`)

---

## Purpose

Define the UX and backend contract for:
- new top navigation workspace: `Juicys`
- optimizer-tab redesign in ticker modal: `Juicy Fruits` table
- refresh flow: schedule async job, then read updated data from Mongo persistence

This workspace is intended to be the daily "spreadsheet" view for evaluating all tracked juicy opportunities across analysis tickers.

---

## Top Nav: `Juicys`

### User Story
As Trader Ken, I want a dedicated `Juicys` main tab where I can scan all actionable opportunities (calls/puts/rolls) in one sortable table, without opening each ticker modal first.

### Requirements
- Add `Juicys` to top nav beside existing dashboard views.
- Route to a dedicated grid workspace (`?view=JUICYS` recommended).
- Default view is `Juicy main` with all juicy items shown.
- Include quick presets:
  - `Juicy Fruit Options`
  - `Hot PUTS` (focused on down-market put opportunities)
- Grid supports sort/filter/search by column and ticker-first scanning.
- Include export/download of current filtered grid.

---

## Ticker Modal Optimizer: `Juicy Fruits` Table

### Layout Contract
Replace card-like optimizer output with a high-density table in the modal Optimizer tab.

### Row Contract (One row per opportunity)
Minimum fields:
- `as_of`
- `ticker`
- `strategy`
- `type` (`CALL`/`PUT`)
- `action` (`BUY`/`SELL`/`ROLL`/`HOLD`)
- `dte`
- `strike`
- `premium`
- `yield_pct`
- `score`
- `reason_summary`

### Chain-Level Candidate Expansion (Implemented)
- For each ticker, generation evaluates option-chain calls across the next `4` expiries.
- Per expiry, selection scope is:
  - `1` nearest ITM call
  - `4` nearest OTM calls
- This yields up to `20` chain-level rows per ticker before adding heuristic rows.
- Persisted chain-level fields include:
  - `premium`
  - `yield_pct`
  - `annualized_yield_pct`
  - `dte`
  - `strike_distance_pct`
  - `timeframe_bucket` (`daily`/`weekly`/`monthly`)
  - `volume`, `open_interest`
  - `bid_ask_spread`, `spread_pct_mid`
  - `liquidity_grade` (`A/B/C/D`)

### Short-DTE + Liquidity Scoring (Implemented)
- Ranking now includes:
  - annualized yield contribution
  - explicit short-DTE boost
  - liquidity-grade contribution
  - spread-cost penalties when spread is large relative to mid
- Outcome: short-duration rows can rank high, but weak liquidity/spread quality suppresses score.

### Interaction Contract
- Default to top `20` rows by score.
- Selector to expand row count: `20`, `50`, `100`, `ALL`.
- Sort and filter on every numeric/text/date column.
- Keep `Analyze` action per row.

---

## Data + Refresh Contract

### DB-First Read
- UI reads from Mongo-persisted opportunity rows first.
- API returns freshness metadata (`last_updated`, `is_stale`, `refresh_queued`, `data_source`).
- Initial paint must not block on live fetch.

### Refresh Action
- `Refresh` button enqueues a background job.
- Job checks yfinance/TWS realtime inputs (source precedence rules apply).
- Job recomputes scores and upserts only:
  - new opportunities
  - changed opportunities
  - better-scored opportunities
- UI shows queued/running/completed status and refreshes from Mongo snapshots when finished.

### Persistence + Truth Engine Alignment
- Store each scored recommendation snapshot with scoring inputs used at that time.
- Preserve enough context to support later grading and hit-rate analysis.
- Align data model with:
  - [Opportunity Persistence & Grading](../learning/opportunity-persistence-and-grading.md)
  - [Opportunity Scoring](../learning/opportunity-scoring.md)

---

## Suggested API Surface (Non-Binding)

- `GET /api/juicys`
  - list workspace opportunities
  - query params: `preset`, `limit`, `sort_by`, `sort_dir`, `ticker`, `strategy`, `min_score`
- `POST /api/juicys/refresh`
  - enqueue refresh job
  - returns `job_id`, queue status, accepted timestamp
- `GET /api/juicys/refresh/{job_id}`
  - job progress/status and summary metrics

Existing endpoint integration:
- `GET /api/portfolio/optimizer/{symbol}` remains valid for per-ticker modal usage, but should return table-ready records.

---

## Scheduler + Audit Requirements

- Add job type: `juicy_refresh_job`.
- Support both manual enqueue and periodic schedule.
- Persist run audit docs with: `job_id`, `queued_at`, `started_at`, `finished_at`, `status`, `source_used`, `rows_scanned`, `rows_upserted`, `errors`.

---

## Acceptance Criteria

- `Juicys` top nav appears and routes correctly.
- Juicys workspace shows Mongo-backed rows without waiting on live providers.
- Modal Optimizer tab uses sortable/filterable table with required columns.
- Default top `20` behavior and row-count selector works.
- Refresh button enqueues background job and surfaces status.
- Completed refresh updates rows when newer/better opportunities exist.
- Opportunity snapshots are persisted for downstream grading analytics.

### Phase 1 Completion Notes
- Chain-level candidate generation and scoring is active in backend `juicy_service`.
- Optimizer modal and Juicys workspace now surface chain qualifiers (`Bucket`, `Ann %`, `Vol`, `OI`, `Liq`).
- Regression coverage added in `tests/test_juicy_service.py` for:
  - 20-row chain generation envelope (4 DTE x 5 rows)
  - combined chain + heuristic candidate set
  - liquidity-grade threshold behavior

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-04-07 | **CREATED** | Captured requirements and contracts for new `Juicys` top nav, Optimizer-table redesign, and refresh-job DB-first workflow |
| 2026-04-07 | **UPDATED** | Implemented chain-depth/liquidity/short-DTE scoring contract (`stock-analysis-optimizer-juicy-table-009..011`) and documented delivered fields + UI exposure |
