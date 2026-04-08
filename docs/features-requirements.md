# Features & Requirements Planning & Roadmap
- When reading this document to perform work:
    - Follow all the rules documented in the workspace rules & workflow .md docs
    - The .gemini global rules rules file should be followed. 
    - When doing work from this document follow the `.agent/workflows/create-a-plan.md` workflow!
    - Create or update existing feature details in docs/features/{feature_name}.md
    - Create or update learning and definitions in docs/learning/{definition_name}.md


> [!NOTE]
> This document serves as the "Wish List" and high-level roadmap for the Juicy Fruit Stock Options project. It is **not** a strict project plan but a collection of Todo items (maybe large feature sets with requirements) to guide future development. Items are not in any particular order. This document should be used like Kanban board per Status Legend to mark items. Avoid use of Epic or waterfall methodologies. Tag or keywords should be related to the NFR or feature-requirement being implemented. 

**Status Legend:**
- [ ] Proposed / Todo
- [/] In Progress
- [x] Done (Move to Changelog)
- [!] Blocked / Needs Research
- [D] Deprecated / Obsolete only for reference

---
# Implementation 
- When performing an implementation plan based on items in this feature-requirements document, i would use the following rules:
-- All the rules documented in the workspace rules & workflow .md docs should be followed
-- This file is a living document of master PRD document for directing coding, all existing features-requirements should be memorialized in this "docs/features-requirements.md" file. Later on this document could be used to generate a whole new green field project from scratch or track where we are in the development of the project went off the rails. 
-- An implementation plan should be broken down into smaller items (added to the feature-requirements.md file as sub items or organized where relevant) that can be completed in a reasonable amount of time 
-- The incremental implementation plan should follow hierarchical decomposition for naming based the short simple name of the feature-requirement. 

## UI/UX Design Standards (Juicy Fruit)
- **Tool to help me**: This is tool to help me trade, track, and identify opportunities in the stock market. I have 3 accounts that I trade in and multiple positions (sometimes duplicate positions) in each account. 
- **Density over Fluff**: Prioritize data tables and comparative metrics over large buttons/empty space.
- **Yield-First**: Every opportunity MUST display an "Annualized Yield %" and "Total Potential Return".
- **Portfolio Positions**: Opportunities and analysis should be able to be filtered or display by account and position VZ (U280132:100 STK, -1 CALL OPT) condensed version with a float over and/or popup (or Detail Drawer) to see other information cost basis, fundementals, and time term status, overall realized and unrealized gains/losses inclusive of any dividends.
- **Comparison View**: Ability to sort, search, and filter tables by any column.
- **No Floating Modals for Core Data**: Use an expandable "Detail Drawer" on the right side of the screen to maintain context of the portfolio list.

## 0. Bugs, Fixes, & Maintenance
- [x] **stock-analysis-broken-202603**: Stock Analysis "Run Live Analysis" feature broken after 2026-03-27 changes. AI_Stock_Live_Comparison XLSX and onscreen grid no longer populate. Investigate `stock_live_comparison.py` and `app/services/stock_live_comparison.py` for root cause. *(Completed 2026-04-03: viable-source-file guard + suspicious low-record save protection + sync-mode viable-base skip behavior.)*
- [x] **stock-analysis-report-churn-20260402**: Stock Analysis keeps generating multiple `AI_Stock_Live_Comparison_*.xlsx` files in the same day (many empty/partial). Enforce trigger-based report file policy and remove duplicate run enqueue. *(Completed 2026-04-03: trigger semantics finalized and regression coverage expanded.)*
    - [x] `run/stock-live-comparison` must enqueue exactly one background job per click.
    - [x] Manual **Run Live Comparison** creates a new timestamped XLSX.
    - [x] Scheduled daily run creates at most one new XLSX per calendar day (reuse same-day file if re-run).
    - [x] Background sync paths (ticker auto-discovery/add ticker) must refresh data without creating a new XLSX file.
- [x] **stock-analysis-valid-source-file-guard-20260403**: When selecting an existing stock analysis XLSX as merge source, ignore suspiciously small/truncated files and prefer the latest viable prior report to prevent truncation snowball.
- [x] **stock-analysis-trigger-policy-tests-20260403**: Add explicit regression tests for manual/scheduled/sync trigger behavior and source-file viability guard so report churn policy does not regress.
- [x] **stock-analysis-yfinance-429-retry-20260403**: Run Live Comparison should gracefully handle transient Yahoo Finance throttling (`HTTP 429 Too Many Requests`) instead of failing each ticker immediately. *(Completed 2026-04-03: fixed retry-loop bug in `fetch_data()` where attempts were never incremented and failures were finalized on first exception; added bounded exponential backoff for retryable yfinance/network errors and regression test in `tests/test_stock_live_methods.py` validating 429 recovery.)*
- [x] **stock-analysis-yfinance-backpressure-20260403**: Add global backpressure and request-volume controls for yfinance so repeated 429 responses do not trigger burst retries across many tickers. *(Completed 2026-04-03: added per-request throttle + global cooldown circuit breaker after 429s, and disabled bulk profile-news fetch in batch runs by default to reduce request count. Added tests in `tests/test_stock_live_methods.py`.)*
- [x] **stock-analysis-yfinance-http-rate-limit-policy**: Enforce an explicit HTTP request-rate policy for Yahoo Finance paths and keep stock-analysis in batch mode to prevent burst traffic (`429 Too Many Requests`). *(Completed 2026-04-07: added scheduler sharded execution wrapper (`run_stock_live_comparison_scheduled`) with configurable shard size/pause read from `system_config` (`_id: stock_analysis_http_config`) and wired the daily `stock_comparison_job` to the wrapper. Added scheduler regression coverage for sharded and non-sharded paths.)*
    - [x] Batch historical downloads in small chunks with controlled parallelism (`threads=True` inside small batches) plus explicit inter-batch delay.
    - [x] Persist downloaded yfinance history locally and reuse fresh cache data, refreshing periodically by TTL to avoid unnecessary HTTP requests.
    - [x] Global 429 cooldown circuit-breaker + jittered retry backoff.
    - [x] Disable bulk profile-news HTTP calls in live batch runs by default.
    - [x] Add scheduler-sharded execution mode (small delayed jobs) so full ticker refresh can be spread over time windows instead of one burst run.
    - [x] Add ops settings in `system_config` for `download_batch_size`, `batch_pause_sec`, and request throttle interval to tune without code changes. *(Completed 2026-04-07: `run_stock_live_comparison` now reads `_id: stock_analysis_http_config` and applies `download_batch_size`, `batch_pause_sec`, `request_throttle_interval_sec` (or legacy `min_request_interval_sec`) into `StockLiveComparison` constructor with safe coercion/default fallback. Added admin settings API at `/api/settings/stock-analysis-http`. Regression coverage in `tests/test_stock_live_comparison_service.py` and `tests/test_data_freshness_routes.py`.)*
    - [x] Add admin UI controls in `Dashboard Settings` for stock-analysis HTTP + scheduler sharding knobs (`download_batch_size`, `batch_pause_sec`, `request_throttle_interval_sec`, `scheduler_sharding_enabled`, `scheduler_shard_size`, `scheduler_shard_pause_sec`).
    - [x] Document manual and API configuration runbook for stock-analysis HTTP/sharding in [Stock Analysis HTTP + Scheduler Sharding Configuration](features/stock_analysis_http_scheduler_sharding.md).
    - [x] Extend sharding behavior to manual **Run Live Analysis** jobs (not just scheduler runs), while preserving single-manual-file semantics by creating a new file on shard 1 and reusing it for subsequent shards in the same run. *(Completed 2026-04-07: added shared `run_stock_live_comparison_with_optional_sharding` path and wired both scheduler + manual endpoint to it. Added regression tests in `tests/test_stock_live_comparison_service.py`, `tests/test_scheduler_jobs.py`, and `tests/test_stock_live_routes_manual_trigger.py`.)*
- [x] **portfolio-live-grid-undefined-values**: Portfolio grid renders JavaScript literal `undefined` for Price, Value, Basis, and Unrealized PnL when merged live+Flex rows have missing fields. Guard all currency/number renders. Tracked under `portfolio-live-grid-001..006`. *(Completed 2026-04-02: formatter guards plus merged-row type/description normalization and regression tests now cover `001..006`.)*
- [x] **events-stk-filter-bug**: Corporate events/xdiv scanner fetches yfinance for OPT contract symbols (e.g., `AMD 260220C00235000`), causing HTTP 404 errors. Filter to underlying STK symbols only before any yfinance fetch. *(Completed 2026-04-02: `generate_corporate_events_calendar` in `dividend_scanner.py` now applies `_normalize_to_stk_symbol` as a final OCC guard after the manual secType filter, deduplicates results. Regression tests in `tests/test_corporate_events.py`: OPT symbol never reaches yfinance, underlying root IS queried, no duplicate calls.)*

## 1. Project Mission & Context
The goal of this project is to build a robust, semi-automated trading dashboard ("Juicy Fruit") that aids **Trader Ken** in analyzing options, managing risk, and executing strategies (e.g., covered calls, wheel strategy). It combines data from IBKR, algorithmic analysis, and modern web technologies.

*   **Reference Docs**:
    *   `.agent/rules/trader-ken.md` (Trading Logic)
    *   `README.md` (Technical Setup)

---

## 2. Infrastructure & Modernization
**Owner:** TBD | **Goal:** reliable, secure, and strictly typed foundation.

### Documentation & Knowledge Management
- [ ] **Mcp server md-converter**: Create tool to convert .md files to .docx for memorization/sharing.
    - [ ] Research `python-docx` vs `pypandoc` for compatibility.
    - [ ] Create CLI entry point or API endpoint for conversion.
- [ ] **Google Docs Migration**: define rules/plans to store non-code docs (blobs, excel) in Google Docs vs Info storage.
    - [ ] **[?] QUESTION**: Do we have a specific Google Service Account or OAuth Client setup, or need one created?
    - [ ] Implement Google Drive API client wrapper.
    - [ ] Define folder structure mapping (Local <-> Drive).
- [ ] **RAG System (Documentation)**: Implement RAG (Retrieval-Augmented Generation) for asking questions about the codebase/docs. `[!] Needs decomposition: min viable scope = ChromaDB + docs/ ingestion only. Full chat interface is a separate downstream item.`
    - [ ] Select Vector Database (e.g., ChromaDB, Pinecone, FAISS).
    - [ ] Develop Document Ingestion Pipeline (Markdown -> Embeddings).
    - [ ] Create Chat Interface for querying docs.

### Dependencies & Package Management
- [x] **IBKR TWS API — Vendored Local Install**: PyPI `ibapi` frozen at 9.81.1 (2020). Resolved by vendoring IBKR source into `vendor/ibapi/` and referencing via local path in `requirements.txt`.
    - [x] Write `ibkr-ibapi-update.sh` — curl + unzip latest `twsapi_macunix.zip` into `vendor/ibapi/`
    - [x] Update `requirements.txt`: replace `ibapi>=9.81.1.post1` with `./vendor/ibapi`
    - [x] Document in `docs/learning/ibkr-ibapi-vendor-install.md`
    - [ ] Commit `vendor/ibapi/` after running the update script for the first time
    - [ ] Add `vendor/ibapi/` commit step to onboarding / new-dev setup notes

### Deployment & Security
- [ ] **Local vs Cloud Analysis**:
    - [ ] Analyze cost/benefit of running Docker on Home PC vs Cloud (AWS/GCP/DigitalOcean).
    - [ ] Identify headache factors (latency, maintenance).
    - [ ] **Budget**: Approximate monthly budget cap for cloud hosting of ~$20, less than $30. 
    - [ ] Create latency monitoring script to test IBKR API response times from cloud regions.
- [ ] **Docker Hardening**: Secure containers when exposed to the internet (ports, user permissions, secrets).
    - [ ] Implement non-root user in Dockerfiles.
    - [ ] Set up Docker Secrets or strict Env Var management (no hardcoded secrets).
- [ ] **Authentication**:
    - [x] Auto-logout in UI if backend token expires, returns view control to login.
    - [ ] Deep link URL to a specific page every page as url target that can copied
    - [ ] Synced session state between generic React usage and Python backend.
    - [ ] Implement "Remember Me" vs "High Security" modes.
- [ ] **Settings Management**:
    - [ ] Admin defaults vs User overrides.
    - [ ] Enforce "minimum safe settings" that users cannot override.
    - [ ] Each user can set their own Timeout for Authentication logout (Admin sets the default to 30 minutes, but can be changed)
    - [ ] Define Configuration Schema (using Pydantic).
    - [ ] Create Frontend UI for editing allowed settings.
    - [x] **setup-config-ui-stock-analysis-http-001**: Dashboard Settings should expose stock-analysis HTTP pacing and scheduler-sharding controls for admin users and include a clear enabled/disabled status indicator for sharding. *(Completed 2026-04-07: Settings modal includes stock-analysis HTTP and scheduler sharding controls plus explicit `Sharding Status: Enabled/Disabled` indicator.)*
    - [ ] **User Preferences**:
        - [ ] Default time view on the `?view=TRADES` page.
        - [ ] Each user can set their own Timeout for Authentication logout
        - [ ] Grid density and column visibility preferences for data-heavy tables.
        - [ ] Theme preference support when/if multiple themes are intentionally supported.
    - [ ] **Operator / Admin Controls**:
        - [ ] Manage feature flags from a controlled settings surface (for example `IBKR_TWS_ENABLED`).
        - [ ] Configure scheduler intervals from validated settings instead of scattered constants.
        - [ ] Securely manage external integration settings and API key references without exposing secret values in the UI.

### Automated Frontend E2E Testing & CI/CD
**Non-Functional Requirement (NFR):** The Modern Standard for all frontend interaction and end-to-end integration testing in the Juicy Fruit project is **Playwright**. All cross-browser, DOM interaction, and UX verification must be automated through this framework.

- [x] **Infrastructure Setup**:
    - [x] `npm install -D @playwright/test` and initialize `playwright.config.js` in the frontend directory.
    - [x] Setup Playwright to run Headless by default (Chromium, Firefox, WebKit) and integrate into Github Actions or local Docker CI.
    - [x] **Workflow & Script Integration**: Update `test-all.sh` to run `npx playwright test` and update `.agent/workflows/test-coverage.md` to include Playwright E2E standards.
- [x] **CI/CD Pipeline Integration**:
    - [x] **GitHub Actions / Docker CI Base**: Create a `.github/workflows/playwright.yml` file to handle automated pull request / push validations.
    - [x] **Headless Automation**: Configure the pipeline to run the Dockerized backend services (MongoDB, FastAPI) alongside the frontend, wait for ports to open, and then execute `npx playwright test`. *(Adjusted to mock network directly via `playwright-manifesto.md` rules).*
    - [x] **CI Test Artifacts**: Capture and store failed test traces, screenshots, and videos generated by Playwright so that any failed test can be interactively debugged via GitHub Actions artifacts.
    - [x] **Agent Workflow Guidance**: Introduce an `.agent/workflows/ci-cd.md` workflow file to guide agents on the rules around modifying CI/CD pipelines, handling mocked API data within tests, and maintaining the GitHub Action yamls.
- [x] **Page Object Model (POM) Pattern**:
    - [x] Ensure agents create/use classes in `frontend/tests/pages/` to abstract UI selectors (e.g., `PortfolioGridPage.js`, `StockAnalysisPage.js`).
    - [x] Limit hardcoded selectors in `*.spec.js` files; mandate POM usage.
- [x] **Mocked Network Reliability**:
    - [x] Tests must use `page.route('**/api/portfolio/**', ...)` to intercept and provide static JSON responses for UI validation, ensuring tests do not fail due to IBKR rate limits or offline states.
- [x] **Session-Focused Test Suites** (Ready for Agent Action):
    - [x] **Auth & Navigation (`tests/specs/nav.spec.js`)**: Test login view, token expiration handling, and sidebar routing.
    - [x] **Stock Analysis Flow (`tests/specs/analysis.spec.js`)**: Test the "Run Live Analysis" button states, row sorting, and spreadsheet download hook.
    - [x] **Portfolio Filters (`tests/specs/portfolio.spec.js`)**: Test Coverage Status (Covered/Uncovered/Naked), Expiring, and Near-Money filter toggles.
    - [x] **Ticker Modal Validation (`tests/specs/modal.spec.js`)**: Verify that clicking a ticker opens the modal, fires the parallel intercept requests, and handles the "Offline" degraded state badge.

### Data Reliability
- [x] **Mongo Backup Automation**: *(Completed 2026-04-07: automation path and backup-storage recommendations documented; current backup workflow is no longer manual-only.)*
    - [X] Automate backup to GitHub (current manual process).
    - [X] Investigate Google Drive as alternative storage.
    - [X] *Action*: Have agent follow `learning-opportunity.md` to recommend best backup practices.
- [x] **Data Freshness & DB-First Read Architecture**: Make database-first reads the default contract for all market-data APIs so frontend speed and integrity do not depend on synchronous external fetches. *(Completed 2026-04-07: DB-first + async refresh + freshness metadata are now baseline contracts with route-level regression coverage.)*
    - [x] **data-freshness-db-first-001**: Enforce DB-first reads for all data-related frontend queries (analysis, ticker detail, opportunities, optimizer, signals, portfolio enrichments). API handlers must query Mongo first and return best-available persisted snapshot immediately. *(Completed 2026-04-07: routes/tests cover persisted-first behavior for ticker analysis, news, opportunity, optimizer, signals, smart-roll, and price-history paths.)*
    - [x] **data-freshness-db-first-002**: If requested fields are stale, queue asynchronous refresh jobs instead of blocking request/response on live external sources. *(Completed 2026-04-07: stale-path responses queue background sync with cooldown-aware dedupe; regression coverage in `tests/test_data_freshness_routes.py` and `tests/test_portfolio_features.py`.)*
    - [x] **data-freshness-db-first-003**: Standardize freshness metadata on API responses: `data_source`, `last_updated`, `is_stale`, `stale_reason`, and `refresh_queued`. *(Completed 2026-04-07: standardized metadata is now validated across core and include-meta endpoints in route regression tests.)*
    - [x] **data-freshness-policy-001**: Define field-level freshness tiers and TTL/SLA windows. *(Completed 2026-04-07: documented tiered SLA policy + endpoint-tier mapping in `docs/features/data_freshness_sla_policy.md`; thresholds are operator-configurable via `/api/settings/data-freshness` and admin UI.)*
    - [x] **data-freshness-policy-002**: Tier A (price-derived fields such as `Current Price`, `% Change`, price-based `P/E`) refreshes on short intraday cadence during market session. *(Completed 2026-04-07: `price_open_min`/`price_closed_min` are validated config settings and route coverage confirms Tier A behavior.)*
    - [x] **data-freshness-policy-003**: Tier B (fundamental periodic fields such as quarterly earnings, analyst targets) refreshes daily or per-report cadence. *(Completed 2026-04-07: `mixed_open_min`/`mixed_closed_min` are validated config settings and route coverage confirms Tier B behavior.)*
    - [x] **data-freshness-policy-004**: Tier C (profile/static fields such as long name, sector, industry) refreshes weekly or on-demand. *(Completed 2026-04-07: `profile_open_min`/`profile_closed_min` are validated config settings and route coverage confirms Tier C behavior.)*
    - [x] **data-freshness-policy-005**: Replace fixed clock assumptions with exchange-session aware logic (market open/closed, early close, holiday calendar) when evaluating staleness. *(Completed 2026-04-07: staleness session logic now handles NYSE open/closed, holiday closures, and common early-close windows.)*
    - [x] **data-freshness-source-rule-001**: Formalize source precedence for stock/instrument freshness: prefer TWS for intraday live price/state when connected; use Flex and yfinance as fallback/backfill based on field type. *(Completed 2026-04-07: source precedence now applies across NAV + holdings paths: recent TWS snapshots drive intraday values, stale TWS holdings snapshots no longer override Flex values, and DB-first endpoints keep yfinance fallback for missing records.)*
    - [x] **data-freshness-source-rule-002**: Keep Flex authoritative for historical/EOD and audit-style records; intraday sources must not rewrite historical truth retroactively. *(Completed 2026-04-07: Flex remains canonical for EOD/historical context while stale intraday TWS snapshots are prevented from overriding canonical Flex holdings/NAV values; regression coverage added for stale TWS merge behavior.)*
    - [x] **data-model-instrument-001**: Keep a lightweight latest snapshot collection per instrument for fast reads and add an append-only price history collection for charting and audits. *(Completed 2026-04-07: stock ingest now persists `instrument_snapshot` latest records per canonical key alongside append-only `instrument_price_history`; DB-first ticker reads can use snapshot freshness when heavy `stock_data` docs are absent.)*
    - [x] **data-model-instrument-002**: Define canonical keying/normalization for instrument identity (`ticker`, case/whitespace normalization, secType-aware keys for options/contracts). *(Completed 2026-04-07: added shared instrument identity service with canonical key builder (`STK:<ticker>`, `OPT:<ticker>:<expiry>:<right>:<strike>`), wired stock price-history persistence to canonical keys with legacy compatibility, and added regression tests.)*
    - [x] **data-model-instrument-003**: Add retention and indexing policy for high-churn history collections (time-based indexes, query indexes, optional rollups) to control storage growth. *(Completed 2026-04-07: instrument collections now enforce query/time indexes (`instrument_snapshot`, `instrument_price_history` incl. `(timestamp desc)`), and scheduled retention cleanup `instrument_price_history_retention_daily` is documented with configurable `price_history_retention_days` policy.)*
    - [x] **data-ingest-scheduler-001**: Add scheduler-sharded ingestion mode so ticker refresh load is spread across time windows and avoids burst traffic/rate limits.
    - [x] **data-ingest-scheduler-002**: Persist ingest telemetry per run (source used, rows updated, stale hit ratio, failures) for operator diagnostics. *(Completed 2026-04-07: stock ingest telemetry payload now includes `source_used`, `rows_updated`, `stale_hit_ratio`, `failure_count`, and `failures` in `stock_ingest_runs`; sharded scheduler summary aggregates `rows_updated` and `failure_count`; regression coverage added in `tests/test_stock_live_comparison_service.py` and `tests/test_scheduler_jobs.py`.)*
    - [x] **data-ingest-scheduler-003**: Add operator settings for freshness intervals and ingest batch controls in validated config (`system_config`) instead of hardcoded constants. *(Completed 2026-04-07: validated API settings endpoints now cover both stock-analysis ingest controls (`/api/settings/stock-analysis-http`) and freshness intervals (`/api/settings/data-freshness`), with admin Dashboard Settings UI controls for both surfaces and regression coverage.)*
    - [x] **data-freshness-tests-001**: Add regression tests proving DB-first behavior: endpoints return persisted data without external dependency when data exists. *(Completed 2026-04-07: coverage includes DB-first persisted paths for ticker analysis/news/signals/optimizer/price-history and cached news without live fetch fallback.)*
    - [x] **data-freshness-tests-002**: Add regression tests for stale-path behavior: stale response includes metadata and queues async refresh without blocking. *(Completed 2026-04-07: stale-path coverage now verifies async refresh queueing + freshness metadata for ticker analysis/news/opportunity/optimizer/smart-roll endpoints.)*
    - [x] **data-freshness-tests-003**: Add integration tests for source precedence and fallback order (TWS connected vs disconnected, Flex/yfinance fallback paths). *(Completed 2026-04-07: coverage now includes TWS recent -> `tws_live`, TWS stale/no snapshot -> `flex_eod`, and DB-missing fallback paths for yfinance-backed routes.)*
- [ ] **IBKR Real-Time Data — IB Gateway Docker Container**: Add IB Gateway as a Docker Compose service for a persistent headless IBKR socket connection. Prerequisite for all TWS real-time tasks below. `[!] Needs decomposition: evaluate whether standalone TWS on host already satisfies all use cases before containerizing. Only proceed if containerized gateway adds measurable reliability.`
    - [ ] **ibkr-tws-gateway-001**: Research and select IB Gateway Docker image (`waytrade/ib-gateway` vs `mvberg`). Validate paper port (4002) and live port (4001). Document in `docs/learning/ibkr-realtime-data-integration.md`.
    - [ ] **ibkr-tws-gateway-002**: Add `ib-gateway` service to `docker-compose.yml` with env vars `TWS_USERID`, `TWS_PASSWORD`, `TRADING_MODE`. Map port 4002. Add VNC port 5900 for dev debugging only.
    - [ ] **ibkr-tws-gateway-003**: Add new env vars to `.env` and `app/config.py` (Pydantic settings): `IBKR_TWS_HOST`, `IBKR_TWS_PORT`, `IBKR_TWS_CLIENT_ID`, `IBKR_TWS_ENABLED` (feature flag, default `false`). Zero disruption to existing Flex pipeline when flag is off.
    - [ ] **ibkr-tws-gateway-004**: Create `ibgateway-config/` directory at workspace root for IB Gateway settings persistence (volume mount). Add to `.gitignore`. Document setup steps in README.

- [x] **IBKR Trader Workstation**: Running localhost on this device. Should be able to handle everything in the docker container stuff. Evaluate running IB Gateway. https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#cpp-static-linking what happens to other logins while gateway is running? Can I still run desktop, TWS, or mobile versions simulaneously? 

- [x] **IBKR TWS API**: Document the data ingest, api, end points for tws  in `docs/learning/ibkr-realtime-data-    .md`. 

- [x] **IBKR Real-Time Data — TWS API Python Service**: Create `app/services/ibkr_tws_service.py` — a thread-safe singleton wrapping `ibapi` for real-time position and account data. Supplements (does NOT replace) `ibkr_service.py` Flex pipeline.
    - [x] **ibkr-tws-service-001**: Add `ibapi` to `requirements.txt`. Verified local installation works with `ibapi==9.81.1.post1` on Dockerfile Python 3.12. Note: `ibapi>=10.19` is not currently available on PyPI.
    - [x] **ibkr-tws-service-CLI**: CLI command line to schedule and test or manually run portfolio or trades sync.
    - [x] **ibkr-tws-service-CLI2**: CLI command to get latest trades or portfolio positions and display them and ideponent upsert into the db. Reviewed 2026-03-31: `app/scripts/ibkr_tws_cli.py` now supports `sync-positions`, `sync-nav`, and `sync-executions` for same-runtime fetch + persistence.
    - [x] **ibkr-tws-service-002**: Implement `IBKRTWSApp(EWrapper, EClient)` with callbacks: `position()`, `positionEnd()`, `updateAccountValue()`, `connectAck()`, `error()`. Follow logging standard: `{datetime} - {filename-class-method} - {LEVEL} - {message}`.
    - [x] **ibkr-tws-service-003**: Implement `IBKRTWSService` wrapper with `connect()`, `disconnect()`, `get_positions()`, `get_account_values(account)`, `is_connected()`. Use `threading.Thread(daemon=True)` for socket loop. Graceful no-op when `IBKR_TWS_ENABLED=false`.
    - [x] **ibkr-tws-service-004**: Register as singleton in `app/main.py` FastAPI lifespan. Connect on startup if `IBKR_TWS_ENABLED=true`, disconnect on shutdown.
    - [x] **ibkr-tws-service-005**: Write unit tests `tests/test_ibkr_tws_service.py`. Mock `EClient`/`EWrapper`. Cover: connect, position callback, account value callback, error handling, graceful degradation when flag is off.
    - [x] **ibkr-tws-service-live-verify**: Verified local CLI connection against live TWS on localhost using port `7496`. `2104`, `2106`, and `2158` startup messages were informational farm-status messages, and `connect-test` returned `"connected": true`.
    - [x] **ibkr-tws-service-ports**: IBGateway uses a different ports configuration than TWS. Reviewed 2026-03-31: documented in `docs/learning/ibkr-realtime-data-integration.md` and `docs/features/ibkr-tws-troubleshooting.md` (`7496/7497` for TWS, `4001/4002` for IB Gateway).
    - [x] **ibkr-tws-webapp-fix-path**: Current web-app failure is no longer treated as a generic UI bug. Treat it as a backend-runtime connectivity/diagnostics issue first, then UI surfacing issue second. See `docs/features/ibkr_tws_realtime.md`, `docs/plans/implementation_plan-20260330-ibkr_tws_realtime.md`, and `docs/learning/ibkr-realtime-data-integration.md`.
        - [x] **ibkr-tws-webapp-fix-001**: Verify realtime from the same runtime as the FastAPI backend, not only from the host shell. Use `status`, `raw-connect-test`, and `connect-test` from `app/scripts/ibkr_tws_cli.py`. Reviewed 2026-03-31 from `stock_portal_backend`: `status --show-env`, `raw-connect-test --force-enable`, and `connect-test --force-enable --client-id 99` all run from the backend runtime and are documented in `docs/learning/ibkr-realtime-data-integration.md`.
        - [x] **ibkr-tws-webapp-fix-002**: Make `/api/portfolio/live-status` the authoritative operator contract for the web app. The response must distinguish `disabled`, `disconnected`, `socket_unreachable`, `handshake_failed`, and `connected`.
        - [x] **ibkr-tws-webapp-fix-003**: Update the frontend portfolio/NAV live status UX to surface `connection_state`, `diagnosis`, and most recent backend failure reason instead of showing a generic "not working" state.
        - [X] **ibkr-tws-webapp-fix-005**: If Docker-to-host TWS remains blocked by trusted-client / localhost-only behavior, explicitly route the web app to the existing Client Portal fallback path rather than leaving the badge ambiguous.
        - [x] **ibkr-tws-webapp-fix-TCP-handshake**: ERROR Still displaying Handshake failed RT mode TCP socket is reachable, but the IBKR API handshake did not complete. Last IBKR error: Not connected. Verify TWS trusted-client / localhost-only API settings for this runtime. Fixed in ibkr tws app settings, API, trusted IPs. 

- [x] **ibkr-tws-data**: Document the tws api and endpoints output, update docs/learning/ibkr-realtime-data-integration.md


- [x] **IBKR Real-Time Data — Scheduler Sync Jobs**: Add APScheduler jobs to sync live TWS positions and NAV snapshots into MongoDB on a continuous intraday basis.
    - [x] **ibkr-tws-jobs-001**: Add `run_tws_position_sync()` to `app/scheduler/jobs.py`. Pull from `IBKRTWSService.get_positions()`, upsert `ibkr_holdings` with `source: "tws"` and `last_tws_update` timestamp. Guard with `IBKR_TWS_ENABLED` flag. Schedule every 30s.
    - [x] **ibkr-tws-jobs-002**: Add `run_tws_nav_snapshot()` job. Pull account values (NetLiquidation, UnrealizedPnL, RealizedPnL) and append to `nav_history` with `source: "tws"`. Schedule every 3 min. **Fixes the 1D NAV showing 0 bug** — intraday data points will now exist.
    - [x] **ibkr-tws-jobs-003**: Tag existing Flex sync documents with `source: "flex"` so consumers can distinguish data freshness. Flex = authoritative for history; TWS = authoritative for current intraday state. Non-breaking additive field.
    - [x] **ibkr-tws-data-source-rule**: Use TWS real-time ingest for current intraday freshness, especially same-day / `1D` portfolio state when Flex reports are stale. Flex remains authoritative for historical and EOD reporting; TWS supplements it for live positions, NAV, and freshness indicators.

- [x] **IBKR Real-Time Data — API Endpoints**: Expose live connection status and data freshness to the frontend.
    - [x] **ibkr-tws-api-001**: Add `GET /api/portfolio/live-status` → returns `{ connected, last_position_update, position_count, tws_enabled }`. Used by frontend health indicator.
    - [x] **ibkr-tws-api-002**: Update `GET /api/portfolio/stats` to include `data_source` (`"tws_live"` or `"flex_eod"`) and `last_updated` timestamp. Frontend uses this to show data staleness.
    - [x] **ibkr-tws-api-003**: Add `GET /api/portfolio/nav/live` returning the latest intraday NAV snapshot from `nav_history` with `source: "tws"` tag.

- [x] **IBKR Real-Time UI**: Make intraday realtime behavior repeatable across `?view=PORTFOLIO` and `?view=TRADES`. When TWS is connected, the UI should surface RT / `1D` freshness from TWS-backed collections and APIs; when TWS is not available, the UI must clearly show the fallback/unavailable reason instead of implying live data exists.
    - [x] **ibkr-tws-ui-rt-001**: Define the data-source rule in docs and API contracts. TWS is the preferred intraday source for RT / same-day freshness, while Flex remains authoritative for historical and EOD reporting.
    - [x] **ibkr-tws-ui-rt-002**: Persist live portfolio snapshots into Mongo with explicit source tags. `nav_history` uses `source: "tws"` for intraday NAV snapshots and `ibkr_holdings` uses `source: "tws"` plus `last_tws_update` so the UI can tell whether `1D` is truly live.
    - [x] **ibkr-tws-ui-rt-003**: Add a dedicated RT/intraday time-series presentation for `?view=PORTFOLIO` that reads from TWS-backed NAV history, distinguishes RT vs `1D`, and never shows placeholder zeroes as real values. Leave the "current nav" widget but add a 'RT' widget with the real time goodies when available, the 1st widget would last EOB from flex
    - [x] **ibkr-tws-ui-rt-004**: Add current-day live trade freshness to `?view=TRADES`. This depends on exposing TWS execution data through API and persisting `ibkr_trades` records with `source: "tws_live"` before Flex history lands.
        - [x] **ibkr-tws-ui-rt-004a**: Treat the current `RT trades are unavailable. TCP socket is reachable, but the IBKR API handshake did not complete.` message as a valid backend diagnosis. Do not degrade it to a generic unavailable state.
        - [x] **ibkr-tws-ui-rt-004b**: Render a trades-specific unavailable state that explicitly tells the operator raw TCP reachability is not sufficient; the IBKR API handshake must complete from the same runtime as FastAPI.
        - [x] **ibkr-tws-ui-rt-004c**: Add backend/runtime verification steps for trades mode using the existing TWS CLI from the same runtime that serves the web app, not just the host shell.
        - [x] **ibkr-tws-ui-rt-004d**: Implement current-day execution ingestion via `reqExecutions`, `execDetails`, and commission reconciliation before enabling RT trades rows or metrics.
        - [x] **ibkr-tws-ui-rt-004e**: Persist `handshake_failed` diagnostics for RT trades so the UI can show the latest failure reason and timestamp without implying missing historical trade data.
    - [x] **ibkr-tws-ui-rt-005**: Surface explicit unavailable states in the UI using backend live-status diagnostics. At minimum support `disabled`, `disconnected`, `socket_unreachable`, `handshake_failed`, and `connected`. Reviewed 2026-03-31: both `PORTFOLIO` and `TRADES` now surface backend live-status diagnostics directly.
    - [x] **trader-ui-fix-TWS-message**: This box is too big for the value free up vertical space and move to the same line as time series selectors, same height, more concise and cleaner UX. This should be able to fix in smaller height and width status box. 
    - [x] **ibkr-tws-ui-rt-006**: Document the exact verification sequence so the feature can be repeated without rediscovery: same-runtime CLI/API connectivity check, scheduler persistence check in Mongo, then frontend validation on `PORTFOLIO` and `TRADES`.

- [x] **IBKR RT Trades Runtime Trust**: Document and operationalize the TWS API trust requirements for the runtime that serves the web app.
    - [x] **ibkr-tws-runtime-trust-001**: Document the exact TWS API settings required for Juicy Fruit runtimes: socket enabled, correct port, trusted client allowance, and the localhost-only implications for Docker or bridged runtimes.
    - [x] **ibkr-tws-runtime-trust-002**: Add an operator checklist that distinguishes host-local success from backend-runtime success and uses absolute pass/fail language for `raw-connect-test` versus `connect-test`.

- [x] **IBKR Real-Time Data — Frontend Freshness Indicator**: Show when portfolio data was last refreshed and whether live TWS is connected.
    - [x] **ibkr-tws-ui-navstat**: Add status badge to `NAVStats.jsx` — green dot = TWS live, yellow = EOD only, grey = disabled. Show `last_updated` as relative time ("updated 12s ago").
    - [x] **ibkr-tws-ui-navstat**: FIX. Current NAV location takes too much vertical realestate, move that to be inside with Sync All Widget button, why is the real time data not showing as working? Reviewed 2026-03-30: compacted Current NAV into the Sync All card and fixed missing TWS `reqAccountUpdates()` subscription so live NAV/account freshness can populate.
    - [x] **ibkr-tws-ui-current**: Can realtime get the current NAV and/or update the 1 day NAV with tws realtime? Reviewed 2026-03-30: yes. `current_nav` now prefers latest TWS NAV snapshot and `1 Day` is recalculated from the Flex 1D start value plus live TWS current NAV.
    - [x] **ibkr-tws-ui-nav-date-001**: `1 Day` card date semantics. Keep `1 Day` anchored to the Flex close batch and show the close date explicitly as "as of COB <date>" (derived from the `NAV1D` `_report_date`, not a generic "Flex Date" label). Implemented via `buildTimeframeSubtitle('1d', timeframe_meta)` in `navStatsUtils.js`; `timeframe_meta["1d"]["end_date_source"]` is always `flex_close`. Tests: `navStatsUtils.test.js` and `test_nav_backend.py::test_get_nav_history_stats_keeps_eod_nav_and_exposes_rt_metrics`.
    - [x] **ibkr-tws-ui-nav-date-002**: `7 Day`, `30 Day`, `MTD`, `YTD`, and `1 Year` end-date semantics. Use realtime "as of" timestamp (`last_tws_update`) only when a fresh TWS NAV snapshot is available; otherwise show the corresponding Flex report date/time for that range. Implemented: `buildTimeframeSubtitle` renders "as of HH:MM ET" for `tws_rt` source, "as of MM/DD" for `flex_report`. Tests: `navStatsUtils.test.js` and `test_nav_backend.py::test_get_nav_history_stats_updates_non_1d_ranges_with_fresh_rt_snapshot`.
    - [x] **ibkr-tws-ui-nav-date-003**: Add explicit source/date metadata fields in `/api/portfolio/stats` so each timeframe can render both value source and end-date source (`flex_close`, `flex_report`, `tws_rt`) without frontend inference. Implemented: `get_nav_history_stats()` returns `timeframe_meta` dict with `value_source`, `end_date_source`, `end_date` per timeframe key. Reviewed 2026-04-02.
    - [x] **ibkr-tws-api-nav-account-001**: Add optional `account_id` query support to `/api/portfolio/stats` and `/api/portfolio/nav/live`. `account_id=ALL` (or omitted) returns portfolio aggregate; a concrete account returns scoped NAV metrics for that account only. Implemented in `routes.py` and `portfolio_analysis.py`; `_normalize_account_id()` handles all/blank → aggregate. Tests: `test_nav_backend.py::test_get_portfolio_stats_supports_account_scope` and `test_get_portfolio_live_nav_supports_account_scope`. Reviewed 2026-04-02.
    - [x] **ibkr-tws-ui-nav-account-001**: Wire the existing Portfolio `Account` dropdown to NAV cards so displayed RT/1D/7D/30D/MTD/YTD/1Y values follow the selected account. `All` must show aggregate totals; a specific account must show only that account's NAV metrics. Implemented: `PortfolioGrid` dropdown calls `onSelectedAccountChange` → `Dashboard.selectedPortfolioAccount` state → `/portfolio/stats?account_id=` re-fetch → `NAVStats` `scopedParams` applied to all card API calls. Reviewed 2026-04-02.
    - [x] **ibkr-tws-ui-nav-compact-001**: Reduce NAV card vertical footprint in `?view=PORTFOLIO` while retaining readability (smaller paddings/heights, concise subtitles, and inline "as of" labeling). *(Completed 2026-04-02: `StatCard` height 62→52px, value font sm/base→xs/sm, Sync All button height 62→52px, NAV font base/lg→sm/base, status text truncated to avoid overflow. `NAVStats.jsx`.)*
    - [x] **ibkr-tws-tests-nav-account-001**: Add backend and frontend regression tests for account-scoped NAV stats and timeframe source/date labeling (including market-open realtime vs Flex fallback branches). Implemented: `tests/test_nav_backend.py` (12 tests, account scope + metadata + RT fallback branches); `frontend/src/components/navStatsUtils.test.js` (5 tests, subtitle formatting + account normalization). All green as of 2026-04-02.
    - [x] **ibkr-tws-portfolio-rt-dedupe-001**: Integrate realtime portfolio items into `?view=PORTFOLIO` with duplicate-safe row merging. Reviewed 2026-03-31: `GET /api/portfolio/holdings` now merges the latest Flex/EOD and TWS/live snapshots by canonical portfolio row key so the grid renders one visible row, prefers fresh live market fields, and retains Flex-only fields such as cost basis when live data does not provide them.
    - [x] **ibkr-tws-trades**: TWS api Are current trades supported can we add that to Sync All and when user clicks the ?view=TRADES 1D time? Reviewed 2026-03-31: live execution capture is now wired through scheduler sync, API endpoints, and the Trade History RT flow.
        - [x] **ibkr-tws-trades-001**: Extend `app/services/ibkr_tws_service.py` to capture live executions and commissions in-memory, expose `get_executions()`, and support idempotent upsert into `ibkr_trades` with `source: "tws_live"`.
        - [x] **ibkr-tws-trades-002**: Extend `app/scripts/ibkr_tws_cli.py` with manual `executions` and `sync-executions` commands for local verification against localhost TWS.
        - [x] **ibkr-tws-trades-003**: Add scheduler job `run_tws_execution_sync()` to request executions and upsert them into `ibkr_trades` on a short intraday interval. Guard with `IBKR_TWS_ENABLED` and make it safe when TWS is disconnected.
        - [x] **ibkr-tws-trades-004**: Add backend API endpoint for live/current-day TWS executions so `?view=TRADES` can explicitly request intraday data freshness without waiting for the next Flex report.
        - [x] **ibkr-tws-trades-005**: Update Trade History UI and Sync All behavior so the trades view can surface current-day TWS executions, show live-vs-Flex source/freshness, and avoid duplicate rows when Flex history later lands.
        - [x] **ibkr-tws-trades-rt-query-normalization**: Reviewed 2026-03-31. Normalize TWS execution `date_time` into `YYYYMMDD HH:MM:SS`, persist `trade_date`, and store signed quantities so current-day `tws_live` queries and RT trade rendering work consistently.
    - [/] **IBKR Pending Orders — Real-Time + Flex-Aware**: Add open / working order ingestion so the portfolio can show pending intent from TWS in real time and optionally blend Flex order-related history only when available. Reference: `docs/features/portfolio_pending_order_coverage.md`, `docs/learning/ibkr-available-data-and-order-models.md`.
        - [x] **ibkr-orders-001**: Extend the realtime IBKR service to request and normalize open / working orders (`openOrder`, `orderStatus`, and related callbacks) into a dedicated pending-order shape keyed by `(account, order_id, perm_id)` where available.
        - [x] **ibkr-orders-002**: Persist TWS working-order snapshots into a dedicated collection such as `ibkr_orders` with explicit `source: "tws_open_order"` and freshness timestamps so the UI can distinguish current pending orders from filled executions.
        - [x] **ibkr-orders-003**: If Flex queries expose order-related rows for this account configuration, ingest them as `source: "flex_order_history"` or similar for backfill / audit only. Flex order rows must not override fresher TWS working-order state. *(Completed 2026-04-07: added conservative Flex CSV/XML order-history parser that upserts `source=flex_order_history` rows for audit/backfill; live pending-order effects now derive from TWS-only working orders.)*
        - [x] **ibkr-orders-004**: Add API support so `?view=PORTFOLIO` can fetch pending-order summaries per `(account, underlying)` group without re-implementing order matching logic in the frontend.
        - [x] **ibkr-orders-005**: Add regression coverage for order normalization across stock orders, single-leg option orders, and roll-like paired orders so merged-source changes do not silently break pending-order visibility. *(Completed 2026-04-03: coverage in `tests/test_api_orders.py` for OCC option parsing, STK fallback quantities, roll-like paired rows, and BAG/combo parent normalization shape.)*
        - [x] **ibkr-orders-006**: Add `?view=ORDERS` with the same role gating as portfolio/trades dashboard controls (`admin`, `portfolio`) and a sortable open-orders table.
        - [x] **ibkr-orders-007**: Enrich orders rows with useful ticker context (`LAST`, `%1D`, skew, momentum/trend fields) so order decisions are not made in a vacuum.
        - [x] **ibkr-orders-008**: Add ticker quick links in orders rows with `D/G/Y` behavior. For option orders, surface underlying stock ticker links and keep detail-modal opening consistent with portfolio analysis flow.
        - [/] **ibkr-orders-009**: Add IBKR Integration setting `Orders Query ID` (`query_id_orders`) and stub Flex order-history sync path; finish with concrete parser mapping once the Flex Orders report is created and verified. *(Updated 2026-04-07: setting + sync path now include conservative generic CSV/XML parser aliases and regression coverage; remaining work is production verification/tight mapping against the account's real Flex Orders report columns.)*
        - [x] **ibkr-orders-010**: Orders UX freshness controls: add manual `Refresh Orders` action, background auto-poll while `?view=ORDERS` is active, and staleness indicator based on `last_order_update` so users can trust displayed order state.
        - [x] **ibkr-orders-011**: Reconcile stale persisted TWS orders after completed open-order snapshots by marking no-longer-open rows `Inactive` (prevents stale BAG/combo parent remnants from appearing as active pending intent).
        - [x] **ibkr-orders-012**: BAG/combo leg decomposition in Orders UI. TWS service captures `comboLegs` from IBKR Contract; `_normalize_order_row` passes them through with `is_bag` flag; `OrdersGrid.jsx` chevron expands per-leg child rows (BUY-to-close / SELL-to-open for 2-leg rolls) with left-border indent; net debit/credit label on BAG limit price. Logic in `ordersViewUtils.js`. *(Completed 2026-04-07)*
        - [x] **ibkr-orders-013**: BAG-parent visibility controls in Orders toolbar: `Show BAG parents` (default ON) / `Show decomposed legs only` (default OFF), mutually exclusive, appear only when BAG orders exist. Logic in `ordersViewUtils.applyBagVisibility`. *(Completed 2026-04-07)*
    - [x] **ibkr-tws-positions-001**: Reviewed 2026-04-02. Persist TWS positions using a contract-level `position_key` (not only `(account, symbol, secType)`) so diagonal/multi-leg option positions on the same underlying do not overwrite each other in memory or `ibkr_holdings` snapshots.
    - [x] **ibkr-tws-ui-002**: Poll `GET /api/portfolio/live-status` every 60s from `Dashboard.jsx`. Update badge state without full page reload.
    - [x] **ibkr-tws-ui-003**: Toast notification if TWS drops from `connected: true` to `connected: false` mid-session.

- [x] **IBKR Real-Time Data Logging & Diagnostics**: Clean up logging so that meaningful and clear auditing, debug and info occurs for success connections, data ingest and errors.
    - [x] **ibkr-tws-logging-001**: Distinguish raw socket reachability from a real IB API session handshake. Log both states explicitly so "`tcp_connectable: true` but `connected: false`" is obvious in backend logs and CLI output.
    - [x] **ibkr-tws-logging-002**: Reclassify routine IBKR informational callbacks (`2104`, `2106`, `2158`) so they do not read like hard errors in logs. Keep true failures such as `504 Not connected` at `ERROR`.
    - [x] **ibkr-tws-logging-003**: Add a single structured "live status snapshot" log line after connect attempts and on scheduler skips. Include `host`, `port`, `client_id`, `connected`, `managed_accounts`, `position_count`, `last_account_value_update`, and `last_error`.
    - [x] **ibkr-tws-logging-004**: Log why realtime persistence does not occur. When `/portfolio/live-status` is false or scheduler jobs no-op, emit the specific cause: disabled flag, no handshake, no managed accounts, no positions, or no account values.
    - [x] **ibkr-tws-logging-007**: Surface the most recent backend TWS failure to the UI/API so the frontend can show a precise state such as "Socket reachable, IBKR handshake failed" instead of a generic "not working".

- [x] **IBKR Real-Time Data — Connection Reliability & Runtime Diagnostics**: Make TWS connectivity repeatable across localhost and Docker-backed runs.
    - [x] **ibkr-tws-reliability-002**: Add a backend/admin verification command or endpoint that runs both `raw-connect-test` and `connect-test` from the same runtime as the API service.
    - [x] **ibkr-tws-reliability-003**: Document and validate the "trusted client origin" requirement for local TWS. Explicitly cover host CLI success vs Docker container failure when TWS only allows localhost or approved IPs.
    - [x] **ibkr-tws-reliability-005**: Add a repeatable runbook for checking live status in order: container env, raw socket reachability, IB API handshake, managed accounts received, account updates received, scheduler persistence, Mongo live snapshot presence, UI status.

- [ ] **IBKR Real-Time Data — Production Hardening Follow-Ups**: Capture the remaining production-readiness items after the core TWS realtime path, docs, APIs, scheduler jobs, and UI diagnostics were completed on 2026-03-31.
    - [ ] **ibkr-tws-hardening-001**: Confirm live persistence end to end in the authenticated web app: successful handshake -> scheduler writes `source: "tws"` docs -> `/api/portfolio/nav/live` returns current NAV -> NAVStats shows intraday freshness.
    - [ ] **ibkr-tws-hardening-002**: If the deployed runtime cannot satisfy TWS trust requirements reliably, route RT trades and other intraday UI paths to an explicit fallback mode instead of presenting a broken live toggle.
    - [ ] **ibkr-tws-hardening-003**: Add an operator-facing diagnostic path for the current failure mode: container can open `host.docker.internal:7496` but TWS only trusts localhost/approved clients, so the IB API handshake never completes.
    - [ ] **ibkr-tws-hardening-004**: Add clear reconnect lifecycle logs: initial connect attempt, successful handshake, disconnect detected, reconnect backoff, reconnect success, and permanent failure after retries.
    - [ ] **ibkr-tws-hardening-005**: Add automatic reconnect with bounded backoff to `IBKRTWSService` so a dropped session does not remain disconnected until process restart.
    - [ ] **ibkr-tws-hardening-006**: Add startup diagnostics that fail loudly when `IBKR_TWS_ENABLED=true` but no successful handshake occurs within the configured warmup window.


- [x] **IBKR Real-Time Data — Client Portal REST API** `[!] Lower priority — fallback only if TWS socket is not viable.` See [IBKR Real-Time Data Integration](learning/ibkr-realtime-data-integration.md) for decision matrix.
    - [x] **ibkr-portal-001**: Downloaded clientportal.gw and running from command line, put this into a docker-compose service. Add `IBKR_PORTAL_ENABLED` feature flag. clientportal.gw$ ./bin/run.sh root/conf.yaml
    - [x] **ibkr-portal-002**: Create `app/services/ibkr_portal_service.py` with session-aware polling: `get_positions()`, `get_summary()`, `keepalive()`. Add `IBKR_PORTAL_ENABLED` feature flag.
    - [x] **ibkr-portal-CLI**: Provide a command line version for testing and checking feature.
    - [ ] **ibkr-portal-003**: Decide whether to register the portal service into FastAPI lifespan / scheduler jobs, or keep it as an on-demand fallback only.
    - [x] **clientportal.gw**: Client Portal requires `clientportal.gw` downloaded Java process. 

- [ ] **TWS API container**: Evaluate need for a dedicated TWS API Docker container for stable IBKR connection, and create more feature-requirement items as neccessary.
    - [ ] Research standard IBC-based containers (e.g., `mvberg/ib-gateway-docker`).
    - [ ] Test reliability of headless TWS vs IB Gateway. 
    - [ ] IBApi The official API for Interactive Brokers provides access to all the data available through IB. Replaces IBPy. interactivebrokers.github.io/tws-api/
    - [ ] IB 2nd user for gateway or tws: https://ndcdyn.interactivebrokers.com/AccountManagement/AmAuthentication



### Observability & Logging
- [x] **Logging**: Implement logging for all backend services. *(Completed 2026-04-07: backend structured logging baseline plus authenticated frontend log-ingest endpoint `/api/logs/frontend`.)*
    - [x] Implement detailed DEBUG - **Style:** preface all logs with "{datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}"    the message text should tell the user what is happening (if possible, include the result of the action)
- [x] **Logging**: Implement logging for all frontend services. 
    - [x] **Frontend centralized logging transport**: Research/send frontend logs to backend API (next step after local boundary logging baseline). *(Completed 2026-04-07: `logFrontendError` now forwards structured payloads to `/api/logs/frontend` with best-effort fallback.)*
    - [x] Implement React Error Boundary logging.
- [x] **Structured Logging:** Use the standard `logging` library.
- [x] **Levels:** `DEBUG` (internal state), `INFO` (milestones), `ERROR` (exceptions with `exc_info=True`).
- [x] **Levels:** `TRACE` for verbose logging (default in Dev), `DEBUG` (default in Prod), `INFO` for milestones, `WARNING` for non-critical issues, `ERROR` for critical issues, `CRITICAL` for system failure. 
- [x] **Traceability:** Verify all errors provide context (e.g., "Failed to process file X due to Y").
- [ ] **Logging:** Implement daily log rotation for log files. *(Evaluated: see [Log Rotation Evaluation](features/log_rotation_evaluation.md) for strategy.)*
---

## 3. Algorithmic Trading Engines
**Owner:** Ken | **Goal:** Automated insights and strategy backtesting.


### Stock Analysis UI
- [x] **Stock Analysis**: Ticker list research grades averages and creates a .xlsx report for download of Call/Put Skew. Is calculated from the nearest 1 Year Option date and 6% Out of The Money (OTM) Strike.
- [x] **Stock Analysis-Call/Put_Skew**: Call/Put_Skew = 1Y6_OTM_CALL_PREMIUM / divided by 1Y6_OTM_PUT_PREMIUM (record in DB 1Y6_OTM_CALL_PREMIUM and 1Y6_OTM_PUT_PREMIUM fields and 1Y6_OTM_CALL_STRIKE and 1Y6_OTM_PUT_STRIKE fields)
- [x] **Stock Analysis**: Run Live Analsis runs the live analysis of a ticker list updates the list.
    - [x] **Stock Analysis**: Bug fix the entire feature quit working after AI_Stock_Live_Comparison_20260327_203220.xlsx  and AI_Stock_Live_Comparison_20260327_165708.xlsx basically yesterday's changees broke this feature as it was previously working. *(Completed 2026-04-03.)*
    - [x] **Stock Analysis**: Report file lifecycle policy — new XLSX only from manual Run Live Comparison or first scheduled run of a day; no extra file creation from ticker sync/update paths. *(Completed 2026-04-03.)*
    - [x] **Stock Analysis**: columns in spread sheet Ticker	Current Price	1D % Change	Market Cap (T$)	P/E	YoY Price %	EMA_20	HMA_20	TSMOM_60	RSI_14	ATR_14	MA_30	MA_60	MA_120	MA_200	EMA_20_highlight	HMA_20_highlight	TSMOM_60_highlight	Ex-Div Date	Div Yield	Analyst 1-yr Target	1-yr 6% OTM PUT Strike	1-yr 6% OTM PUT Price	1-yr 6% OTM CALL Strike	1-yr 6% OTM CALL Price	Annual Yield Put Prem	3-mo Call Yield	6-mo Call Yield	1-yr Call Yield	Annual Yield Call Prem	Call/Put Skew	6-mo Call Strike	Error	Last Update	_PutExpDate_365	_CallExpDate_365	_CallExpDate_90	_CallExpDate_180	MA_30_highlight	MA_60_highlight	MA_120_highlight	MA_200_highlight *(Completed 2026-04-07: persist 1Y 6% OTM call/put strike+price for historical audits.)*
    - [x] **Stock Analysis — Skew Formula**: Define `Call/Put Skew` as `1Y6_OTM_CALL_PREMIUM / 1Y6_OTM_PUT_PREMIUM` (call premium divided by put premium), with nearest tradable strike selected at or beyond the 6% OTM target. Example verification: `28.40 / 19.79 = 1.435...` (about `1.44`). Strike selection rule: call uses first listed strike `>= current_price * 1.06`; put uses last listed strike `<= current_price * 0.94`. This allows non-exact 6% strikes (for example target call strike `265` may resolve to listed `270`, target put strike `245` may resolve to listed `240`). *(Completed 2026-04-07.)*
    - [X] **Stock Analysis**: Create a spreadsheet for downloading AI_Stock_Live_Comparison_YYYYMMDD_HHMMSS.xlsx with all the columns store a copy in the local file system. 
    - [X] **Stock Analysis**: Put most of the columns in the spreadsheet into a onscreen table for interactive viewing, sorting, and filtering. Ticker, Last/Current Price, Call/Put Skew (6% OTM 1 YR Options), YoY % (Year over Year percentage), TSMOM 60 (Time Series Momentum - 60 day), 200 MA (200-day Moving Average), EMA 20 (20-day Exponential Moving Average), HMA 20 (20-day Hull Moving Average), Div Yield 
    - [X] **Stock Analysis**: Default sort is by Call/Put Skew (6% OTM 1 YR Options) from highest to lowest.
    - [X] **Stock Analysis**: Link ticker's Call/Put Skew opens tab to Yahoo Options Chain for that STK. 
    - [x] **Run Live Analysis**: Disables button while analysis is running. Changes to "running" until ready again, reloads the grid.
    - [x] **Run Live Analysis**: Create/Add, Delete, Update Ticker List. 
    - [x] **Portfolio items**: Disable the Delete button for portfolio items so they stay persistant, maintain security of the portfolio for other non users, don't reveal any additional sensitive information.
    - [x] **Stock Analysis — Ticker Quick Links**: Add the standard ticker quick links directly on the `?view=ANALYSIS` page ticker column so each analysis row exposes Google Finance, Yahoo Finance, and Stock Analysis detail/modal actions without requiring manual navigation elsewhere. *(Completed 2026-04-02: `LinkRenderer` in `StockGrid.jsx` now shows `G` / `Y` icon links matching the PortfolioGrid/TradeHistory pattern; ticker text opens TickerModal.)*
    - [x] **Tickers — Composite Rating**: Aggregate all ticker metrics (momentum TSMOM_60, Call/Put Skew, news sentiment, technicals EMA/HMA/MA, RSI, ATR) into a single "Ticker Health" score column in the StockGrid. Should be color-coded (green/yellow/red) and sortable. Currently no composite score exists in the grid. *(Completed 2026-04-03: weighted score includes technicals + optional sentiment/macro inputs, sortable color-coded StockGrid column.)*
    - [x] **Stock Analysis — Ticker Click Popup**: Pop-up modal (`TickerModal.jsx`) when clicking a ticker in StockGrid or PortfolioGrid. See [Ticker Click Feature Overview](features/stock_analysis_ticker_click.md). **Implemented:** 6-tab modal with parallel API fetches. **Source:** `TickerModal.jsx`, `Dashboard.jsx`.
        - [x] **Backend API — Ticker Data**: `GET /api/ticker/{symbol}` — returns stock data from MongoDB `stock_data` collection (`routes.py` L1090).
        - [x] **Backend API — Opportunity**: `GET /api/opportunity/{symbol}` — returns Juicy Score, drivers, risks, metrics (`routes.py` L1112).
        - [x] **Backend API — Optimizer**: `GET /api/portfolio/optimizer/{symbol}` — returns ranked strategy suggestions (`routes.py` L1168).
        - [x] **Backend API — Smart Rolls**: `GET /api/analysis/rolls/{symbol}` — returns roll suggestions with scoring (`routes.py` L816).
        - [x] **Backend API — Signals**: `GET /api/analysis/signals/{symbol}` — returns Kalman + Markov analysis (`routes.py` L1038).
        - [x] **Frontend — TickerModal UI**: 6 tabs (Analytics, Signals, Opportunity, Optimizer, Price Action, Smart Rolls) with loading spinner and dark theme. `TickerModal.jsx`.
        - [x] **Frontend — TickerModal Copy Info**: Add `COPY INFO` action in detail modal header to copy header context (ticker/descriptor/price/change/last update) plus currently active tab details (Analytics/Signals/Opportunity/Optimizer/Price Action/Smart Rolls/Profile). *(Completed 2026-04-07: `TickerModal.jsx` adds tab-aware clipboard payload builder and copy feedback states.)*
        - [x] **Frontend — StockGrid Integration**: Ticker column click handler passes ticker to Dashboard state → opens modal. `StockGrid.jsx` + `Dashboard.jsx`.
        - [x] **Frontend — PortfolioGrid Integration**: Ticker click in portfolio view also opens the same TickerModal. `PortfolioGrid.jsx`.
        - [x] **All ~40 Columns in Analytics Tab**: The Analytics tab currently shows a subset of data. Expand to surface all ~40 analysis columns from the stock analysis spreadsheet. *(Completed 2026-04-03: analytics tab renders full stock-analysis field groups via shared presentation config.)*
    - [x] **Stock Analysis — Feature Docs**: See [Ticker Click Feature Overview](features/stock_analysis_ticker_click.md) and [Stock Analysis Recap](features/stock_analysis_feature_recap.md).
    - [x] **Stock Analysis-Analytics Layout Refinement**: Refine Analytics tab information layout for readability and scan speed — clearer section hierarchy, improved spacing/alignment, consistent label/value widths, and better grouping for high-priority metrics vs supporting metrics. *(Completed 2026-04-08: analytics tab now includes high-priority summary metric cards, card-based grouped sections, and fixed-width label/value row alignment for faster scanning.)*
    - [x] **Stock Analysis-Copy Output Enhancement**: Refine `COPY INFO` output layout so copied text is easier to share/read — consistent section headers, ordered fields, cleaner spacing, normalized numeric/date formatting, and tab-specific summary blocks. *(Completed 2026-04-08: `COPY INFO` now emits normalized section blocks (`[Header]`, tab-specific sections) and standardized numeric/date formatting through shared presentation helpers.)*
    - [ ] **Stock Analysis-Analytics**: Deeper technical analysis drill-down in the Analytics tab — IV surface visualization, Greeks heatmap, historical metrics comparison, and all moving average highlight deltas. Related: [SMA/EMA/HMA/TSMOM Guide](features/SMA-EMA-HMA-TSMON.md), [Greeks Data Ingestion](learning/greeks-data-ingestion.md).
    - [ ] **Stock Analysis-Signals**: Expand Signals tab beyond Kalman/Markov to include news sentiment signals ([LLM Macro Targeting](learning/llm-macro-news-targeting.md)), macro impact scoring, and TSMOM trend alerts. Related: [Kalman Filters](learning/kalman-filters.md), [Markov Chains](learning/markov-chains-signals.md).
    - [x] **Stock Analysis-Opportunities**: Surface actionable Buy/Sell recommendations in Opportunity tab — dividend capture candidates, covered call premium opportunities, and gap share alerts. Integrate with `DividendScanner` and `ExpirationScanner`. Related: [Opportunity Scoring](learning/opportunity-scoring.md), [Opportunity Persistence & Grading](learning/opportunity-persistence-and-grading.md). *(Completed 2026-04-07: `GET /api/opportunity/{symbol}` now returns actionable recommendation rows plus related persisted scanner opportunities from `opportunities` collection and Opportunity tab renders these sections.)*
    - [x] **Stock Analysis-Optimizer**: Multi-leg strategy optimizer in Optimizer tab — risk/reward visualization, what-if scenario analysis (price up/down), and yield comparison across strategies. Related: [Smart Roll & Diagonal](learning/smart-roll-diagonal.md). *(Completed 2026-04-07: optimizer now uses persisted juicy candidate rows with score/yield fields and table-first rendering.)*
        - [x] **stock-analysis-optimizer-juicy-table-001**: Replace card-like optimizer panel with a dense spreadsheet-style table in the ticker detail modal Optimizer rename the tab ("Juicy Fruits" list) so rows can be sorted and filtered by any column. *(Completed 2026-04-07: tab renamed `Juicy Fruits`; sortable/filterable spreadsheet table implemented in `TickerModal.jsx`.)*
        - [x] **stock-analysis-optimizer-juicy-table-Same-as-NAV**: Ticker detail Juicy/Optimizer tab should be the same data base logic as the main top NAV "Juicy-Nav" tab but just showing current Ticker only. *(Completed 2026-04-07: both modal and top-nav `Juicys` use `GET /api/juicys` / persisted `juicy_opportunities` contract; modal uses ticker-filtered `/api/portfolio/optimizer/{symbol}` built on same persistence.)*
        - [x] **stock-analysis-optimizer-juicy-table-002**: Optimizer table columns must include at minimum: `as_of`, `strategy`, `type` (`CALL`/`PUT`), `action` (`BUY`/`SELL`/`ROLL`/`HOLD`), `dte`, `strike`, `premium`, `yield_pct`, `score`, and `reason_summary`. *(Completed 2026-04-07: backend payload and modal/juicys grids include required columns plus audit dates.)*
        - [x] **stock-analysis-optimizer-juicy-table-003**: Default optimizer tab view should show top `20` ranked opportunities per ticker (single row per candidate) with a selector for `20/50/100/ALL`. *(Completed 2026-04-07: default top 20 with selector in modal.)*
        - [x] **stock-analysis-optimizer-juicy-table-004**: Include preset filters for "Juicy Fruit Options" (general best score) and "Hot PUTS" (down-market put opportunities) and allow combining with column filters. *(Completed 2026-04-07: preset buttons + text column filter in modal; same presets in Juicys nav workspace.)*
        - [x] **stock-analysis-optimizer-juicy-table-005**: Add Optimizer tab `Refresh` button that enqueues async refresh work (yfinance/TWS as available), immediately returns queued status, and refreshes UI from Mongo once newer/better-scored rows persist. *(Completed 2026-04-07: `POST /api/juicys/refresh` queue path wired to modal and Juicys workspace refresh controls.)*
        - [x] **stock-analysis-optimizer-juicy-table-006**: Optimizer tab stays DB-first: reads from Mongo persisted opportunities first, returns freshness metadata, and never blocks tab render on live network calls. *(Completed 2026-04-07: optimizer reads `juicy_opportunities` first and returns include-meta freshness contract.)*
        - [x] **stock-analysis-optimizer-juicy-table-007**: Persist full optimizer candidate snapshots and scoring inputs so each recommendation can be replayed/graded later (align with [Opportunity Persistence & Grading](learning/opportunity-persistence-and-grading.md) and [Opportunity Scoring](learning/opportunity-scoring.md)). *(Completed 2026-04-07: persisted fields include `scoring_inputs`, `create_date`, `last_updated`, and stable `strategy_key`.)*
        - [x] **stock-analysis-optimizer-juicy-table-008**: Upon clicking on an individual Ticker details (whether the user selects Juicy/optimizer tab or not) each opportunity should have a create_date and last_updated, if the last update is greater than the most recent close of the market or it's during the active trading time then update the juicy list if the last update is greater than 30 minutes. IE go pull new option chains for the underlying ticker (this should be scheduled as async job and should NOT hold up the display of current or whatever data is available at the time) *(Completed 2026-04-07: modal prefetch hits optimizer endpoint; stale checks enqueue async juicy refresh job and returns current persisted rows immediately.)*
        - [x] **stock-analysis-optimizer-juicy-table-009-option-chain-depth**: Expand per-ticker juicy generation beyond the current top-level heuristic rows into option-chain level candidates. For each of the next `4` DTE dates, evaluate `1` nearest ITM call and `4` nearest OTM calls for sale; persist each candidate with `premium`, `yield_pct`, `annualized_yield_pct`, `dte`, and strike-distance metadata. *(Completed 2026-04-07: `build_chain_level_call_candidates()` now builds/persists up to `20` chain rows per ticker (4 expiries x 5 calls) and includes strike-distance + annualized yield fields.)*
        - [x] **stock-analysis-optimizer-juicy-table-010-liquidity-qualifier**: Add liquidity/timeframe qualifiers to optimizer scoring so chain candidates are graded by daily/weekly/monthly tradability quality. Minimum tracked fields: `volume`, `open_interest`, `bid_ask_spread`, `spread_pct_mid`, and a derived `liquidity_grade` (`A/B/C/D`) used in final score ranking and UI badges. *(Completed 2026-04-07: chain candidates persist `volume/open_interest/bid_ask_spread/spread_pct_mid`, derive `liquidity_grade`, and include `timeframe_bucket` (`daily/weekly/monthly`) in score inputs and UI columns.)*
        - [x] **stock-analysis-optimizer-juicy-table-011-short-dte-focus**: Add explicit short-DTE ranking mode so high-yield short duration candidates are surfaced first but penalized when liquidity quality is weak or spread cost dominates premium edge. *(Completed 2026-04-07: chain scoring combines annualized yield + short-DTE boost + liquidity grading with spread penalties; ranked rows now bias toward short-DTE only when execution quality is acceptable.)*
    - [ ] **Stock Analysis-Price_Action**: Interactive price action charting in Price Action tab — ZigZag algorithm overlay, supply/demand zone visualization, Break of Structure (BOS) annotations, and Order Block/FVG zones on chart. Related: [Price Action Concepts](learning/price-action-concepts.md), [Price Action Plan](plans/implementation_plan-20260202-price-action.md).
    - [x] **Stock Analysis-Header**: The existing header on the popup window shows OLN $23.41 -0.93%% (Ticker, Price, % Change) Include full name or description of the ticker.   (Ticker, Description, Price, % Change, Date/Time of last update), Make a link from the TICKER to finance.google.com/quote/{TICKER} and the Description to https://finance.yahoo.com/quote/{TICKER}/ See [Implementation Plan](plans/implementation_plan-20260328-stock_analysis_header.md). *(Completed 2026-04-02: `TickerModal` header now uses normalized ticker/descriptor/price/change/timestamp model with `-0.93%` formatting fix and link targets.)*
    - [x] **Stock Analysis**: Add a new sub-tab for Profile, Include company Description, Sector, Style, Industry, other relevant profile information. Link to https://finance.yahoo.com/quote/{TICKER}/news/ See [Feature Doc](features/stock_analysis_profile_tab.md) | [Implementation Plan](plans/implementation_plan-20260328-stock_analysis_profile_tab.md). Profile refreshed on Run Live Comparison (manual) or daily schedule; lazy-hydrated on first ticker open if absent.
    - [x] **Stock Analysis Data Persistence**: Persist complete per-ticker analysis payloads used by detail APIs so runs/schedules and modal retrieval stay aligned. *(Completed 2026-04-03: `upsert_to_mongo` now writes canonical docs to `stock_data` keyed by `Ticker`, preserves existing nested detail payloads when merge rows are sparse, and records `_last_persisted_at`.)*
        - [x] **stock-analysis-db-001**: On manual and scheduled Run Live Analysis, persist the full analysis field set per ticker into `stock_data` (not only spreadsheet output). *(Completed 2026-04-03: canonical ticker upsert key changed from `(Ticker, Last Update)` to `Ticker` in `stock_data`.)*
        - [x] **stock-analysis-db-002**: Persist profile/news detail fields required by ticker modal tabs so hydration/fallback is deterministic and not dependent on live external fetches. *(Completed 2026-04-03: sparse incoming rows now preserve existing `profile` and `Price Action` payloads during persistence merge.)*
        - [x] **stock-analysis-db-003**: Add persistence completeness regression tests that assert required field presence for ticker detail endpoints after ingestion. *(Completed 2026-04-03: coverage added in `tests/test_stock_live_methods.py` for canonical stock_data upsert, detail-payload merge preservation, and required field checks including `profile.news`.)*
    - [x] **Stock Analysis Detail loading...**: Loading price/details now resolve from local DB for normalized ticker variants (case/whitespace) and option-like symbols routed from Portfolio/Trades views; fixed "No data found for this ticker." modal false negatives. *(Completed 2026-04-03: backend `/api/ticker/{symbol}` adds normalized + relaxed ticker lookup fallback; Portfolio ticker click now routes canonical underlying ticker.)*
        - [x] **stock-analysis-detail-001**: Canonicalize ticker detail symbol routing from multi-security grids (STK/OPT) so modal requests always use underlying equity symbol.
        - [x] **stock-analysis-detail-002**: Add backend fallback ticker lookup (`exact` then case/whitespace-insensitive match) before returning `found=false`.
        - [x] **stock-analysis-detail-003**: Add regression coverage for relaxed ticker matching and option-like symbol normalization in `/api/ticker/{symbol}` tests.
    - [x] **Ticker Modal Resilience (Analysis Popup)**: Modal should remain responsive even when one or more tab endpoints are slow/unavailable.
        - [x] **ticker-modal-resilience-001**: One slow endpoint no longer blocks the entire modal (`Analyzing...`) spinner. *(Completed 2026-04-03: switched from all-or-nothing `Promise.all` to settled per-endpoint handling with request timeouts.)*
        - [x] **ticker-modal-resilience-002**: Add hard-stop loading guard so modal spinner exits within bounded time under degraded network/API conditions. *(Completed 2026-04-03: bounded loading watchdog added in `TickerModal.jsx`.)*
        - [x] **ticker-modal-resilience-003**: Handle browser offline mode explicitly (`navigator.onLine === false`) with immediate non-blocking fallback state.
        - [x] **ticker-modal-resilience-004**: Add visible UI reason badges/messages for per-tab degraded states (`timeout`, `offline`, `endpoint unavailable`, `stale local data`) instead of silent empty sections. *(Completed 2026-04-07: TabErrorBadge component; classifyTabError/getBadgeText in tickerModalResilience.js; tabErrorReasons state per-tab; renderTabPanel shows badge on error state.)*
        - [x] **ticker-modal-resilience-005**: Add frontend regression tests for guaranteed spinner exit and settled partial-render behavior when one endpoint is intentionally delayed/failing. *(Completed 2026-04-07: tickerModalResilience.test.js covers timeout/offline/endpoint/partial-render/watchdog scenarios using node:test.)*
    - [x] **Stock Analysis Run Observability & Stuck-Job Recovery**: Improve visibility and fail-safe behavior when **Run Live Analysis** appears stuck (button grayed out) so operators can distinguish active progress vs stalled job.
        - [x] **stock-analysis-run-obs-001**: Add explicit backend run lifecycle logging (`start`, ticker count, periodic progress checkpoints, completion summary) for stock live comparison flow. *(Completed 2026-04-03: `app/services/stock_live_comparison.py` + `stock_live_comparison.py` now emit run/fetch progress logs.)*
        - [x] **stock-analysis-run-obs-002**: Add stale-running auto-fail watchdog behavior for stock live analysis jobs so previously hung runs are surfaced and cleared before new queueing. *(Completed 2026-04-03: `/run/stock-live-comparison` marks stale running jobs failed before queueing a new run.)*
        - [x] **stock-analysis-run-obs-003**: Add latest stock-run job status endpoint for UI/polling diagnostics (`GET /api/jobs/latest/stock-live-comparison`). *(Completed 2026-04-03.)*
        - [x] **stock-analysis-run-obs-004**: Wire frontend to recover grayed-out Run button from stale status using latest-job endpoint fallback and show explicit reason text (`running`, `timed_out`, `stale_watchdog_failed`, `failed`). *(Completed 2026-04-07: Dashboard.jsx polls `GET /api/jobs/latest/stock-live-comparison` on mount and every 15s while running; `runObsUtils.js` provides shared state-derivation logic tested via `runObsUtils.test.js`.)*
    - [x] **Stock Analysis Detail loading telemetry**: Add explicit modal-level error badge/logging when detail fetch returns `found=false` so unresolved symbols can be diagnosed quickly in UI support workflows. *(Completed 2026-04-08: ticker modal now shows a diagnostic warning badge when detail lookup returns `found=false` and sends one-shot structured frontend telemetry payloads to `/api/logs/frontend`.)*

### Portfolio Management UI
- [x] **Portfolio Analytics**: Show Key Performance Indicators (NAV, d/w/m/y changes) on the Portfolio Dashboard (via `NAVStats`).
- [ ] **Portfolio History Visualization**: Implement interactive time-series chart for NAV performance.
    - [ ] **Frontend**: Add graph component (e.g., Recharts) to "My Portfolio" view using data from `/portfolio/stats` (history field).
    - [ ] **Business Logic**: Implement Cost Basis and Realized P&L calculation (grouping buys/sells by symbol).
    - [ ] **Ticker Analytics**: Sneak peek at the ticker analytics endpoint (ie: `/ticker/{symbol}`) to show the most recent stats for an individual ticker. A modal window that pops up an overlay with 
    - [ ] **Opportunity Finder**: Implement Opportunity Finder (ie: `/opportunity/{symbol}`) to show the most recent stats for an individual ticker. 
    - [ ] **Portfolio Optimization**: Implement Portfolio Optimization (ie: `/portfolio/optimizer/{symbol}`) to show the most recent stats for an individual ticker. 
    - [x] **Bug Issue**: Adding stock ticker to analysis doesn't add the ticker to the active screen list, logs indicate a new file is created. A screen refresh reload shows this file at the top of the list. **Fixed**: Added job polling to `handleAddTicker` to wait for file generation and auto-refresh the report list.
    - [x] **Bug Issue**: UI for Portfolio could be wider so it doesn't require horizontal scrolling. Additionally the width of the Qty field is too wide for the size of qty and max size like doubtful that I would have more than 99,999 shares of a stock or option. Type field doesn't have to be that wide. Account doesn't need to be much wider than width of the title name. Whereas the ticker field would be better if it was wider **Fixed**: Optimized column widths in `PortfolioGrid.jsx`. Increased Ticker width (140->200), reduced Account, Qty, Type widths. Removed auto-flex to respect manual sizing. 
- [/] **Frontend**: Create a new modal window that pops up an overlay with the ticker analytics, opportunity finder, and portfolio optimization data that uses all news, stock data, and option data to provide a comprehensive view of the ticker, all the anlytics and opportunity finder data should be in the modal window. Integration to agent chat allow the user ask questions about the ticker and get a response based on the data in the modal window. 
    - [ ] **Ticker Details** Should aggregate News and details 
    - [ ] **Ticker Details** Should aggregate Opportunity Finder data 
- [x] **My Portfolio** Window screen size seems smaller than the analysis page causing the grid to have to horizontally scroll.  Can we increase the size of the screen size of the My Portfolio page to match the analysis page or the size of the screen, we have plenty of extra room. What's logical given we are going to be adding features and ui stuff? *(Completed 2026-04-08: portfolio grid panel now scales with viewport height (`calc(100vh-220px)`, `min-h: 700px`) so the workspace uses available screen real estate more consistently.)*  

- [x] **Trade History Management**: Get entire history of trades (ie: with cost basis) and all relevant metrics
    - [x] Ingest Legacy Trade Files (See [Legacy Trade Ingestion](features/legacy_trade_ingestion.md))
    - [x] **Backend API**: Create `/api/trades` endpoint to serve historical data with pagination/filtering.
    - [x] **Business Logic**: Implement Cost Basis and Realized P&L calculation (grouping buys/sells by symbol).
    - [x] **Frontend**: Build "Trade History" view with datagrid, filtering, and export.
    - [x] **Metrics**: Add summary metrics (Total P&L, Win Rate, LT/ST P&L, etc.) to the history view.
    - [x] **Bug issue**: History view is not loading trades, 500 Internal Server Error http://localhost:3000/api/trades/analysis
    - [x] **Bug issue**: Portfolio view sub menu is dropping down when going to the trades menu tab. 
    - [x] **Trade Metrics Education**: See [Trade Metrics Guide](learning/trade-metrics.md). Explains Win Rate, Profit Factor, Diagonal Rolls, and Dividends.
    - [x] **time window**: For trade history view, can we implement a time window starting with MTD, having 1D, 1W, 1M, 3M, 6M, 1Y, 5Y,and All trades?
    - [x] **view=TRADES**: add metric widget for Unrealized Profit and Unrealized Loss for each timeframe. Update Total trades to show Open = ## & closed = ## trades (update Trade Metrics Guide](learning/trade-metrics.md )
    - [x] **trade history**: Group by account # and related option trades. 
    - [x] **trade history / dividends**: Can we add dividends to the trade history view? Dividends currently come in via the NAV reports, but a dedicated report is needed for granular ticker-level detail. *(Updated 2026-04-02: backend now emits explicit dividend trade rows (`source: dividend`, `asset_class: DIV`) and TradeHistory renders them as distinct cash events.)*
        - [x] **New Flex Report**: Configure a new custom Flex Query in IBKR specifically for Cash Transactions (Dividends).
        - [x] **Data Requirements**: The flex report must extract `AccountId`, `Date`, `Symbol`, `Amount` (Total dividend amount), `Currency`, and `Type/Description` (to identify cash dividends vs other cash movements). Added Flex report Activity Flex Query Details Query ID		1434041 Query Name		Dividend_Report (update settings page with this info also) (see [IBKR Flex Report Dividends](learning/ibkr-flex-report-dividends.md)) 
        - [x] **Backend Parser**: Update `ibkr_service.py` to parse this new report and store dividends historically in the database, tying them directly to each stock symbol.store as much of the data as possible (dates and details if you have to create a new collection dedicated to dividends that do that also.) *(Completed 2026-04-02: `parse_csv_dividends` upserts into `ibkr_dividends`; regression coverage added in `tests/test_ibkr_service_dividends.py` for PO/RE + date normalization + idempotent key fallback.)*
        - [x] **Trade History View**: Add dividends to the trade history flow, either as distinct transaction lines or as a new metric. *(Completed 2026-04-02: `/api/trades` and `/api/trades/analysis` include mapped dividend cash rows; tests in `tests/test_api_trades.py`.)*
        - [ ] **Portfolio View Integration**: Include the historical dividend details in the "My Portfolio" view so that Total Return, True Yield, and Cost Basis accurately reflect the yield generated by the stock.
    - [x] **trade history**: Bug when changing the time frame the window data response takes a while, furthermore the http transaction shows the response as "pending". Further the account is not displaying the correct account # for the trades. 
    - [x] **trade history counts**: The metrics (Total Trades, Open Trades, etc.) are miscalculated due to counting every `realized_pl == 0` leg as an open trade. 
    - [x] **trade history enhancements**: Add AssetClass (STK vs OPT), Put/Call, NetCash, ClosePrice, and Exchange fields to the Trades Query data synchronization. (See [Implementation Plan](plans/implementation_plan-20260314-trades_analysis_enhancements.md))
    - [x] **trade history UI**: Trades widget Total (789) Open: 522 Closed: 762 show total and open closed details for each account make the font smaller to fit inside the widget. (See [Walkthrough](plans/walkthrough-20260321-trade_history_account_metrics.md))
    - [x] **trade History UI**: Set default as YTD instead of ALL 
    - [x] **trade history UI**: Total Trades  collapse the fonts for Total Trades Change the title to Trade Count, list should be All   T:932 O:378 C:916 , Account1, T:204 O:72 C:202, Account2, T:458 O:186 C:450, Account3, T:270 O:120 C:264
    - [x] **trade history UI**: fix Trade Count add a line break between All and Account1, <BR>Account2, <BR> Account3 (between each break out line item.
    - [x] **trade history UI**: All the widgets should have a ALL amount, <br> Acct1 amount, <br> Acct2 amount break out 
    - [x] **trade history UI**: Fix Unrealized P&L does not update when switching the time frame. 
    - [x] **trade history UI — Ticker Quick Links**: Add the standard ticker quick links on the `?view=TRADES` page ticker column so each trade row exposes Google Finance, Yahoo Finance, and Stock Analysis detail/modal actions directly from trade history.
    - [x] **trade history UI — Ticker Column Width**: Size the ticker column on `?view=TRADES` wide enough for long OPT contract symbols plus 3 quick-link actions. Default sizing should avoid manual resizing, clipping, overlap, or hidden link actions.

### Portfolio 
- [x] **Portfolio View**: Remove all the opportunities from the portfolio view (the entire grid)
- [ ] **Portfolio View**: Add a new filter system portfolio list that allows filtering by STK/OPT groups that are not fully covered and other useful items. UI should allow user to focus useful items and take action on them.  view=PORTFOLIO page.
    - [x] **Options Due in X Days**: Signal for all options expiring in <#N (default 6) Days (DTE). Verify and update the scanner to ensure it is working as expected and passes tests Update plan if changes are needed. *Backend Implemented via `ExpirationScanner`.* Portfolio grid toolbar now supports an `Expiring (<ND)` toggle that combines with coverage status, near-money, and account filters using `AND` logic.
    - [x] **OTM / Near Money filter**: ITM In The Money & OTM Out of the Money filter for portfolio options including the underlying_symbol STK, given % distance between option strike and underlying stock price, and show all contracts that are "near" the money to focus on. Portfolio grid now supports a `Near Money (<N%)` toggle that combines with the other active portfolio filters using `AND` logic. Default threshold is `8%`, adjustable from `0` to `20`. The calculation must use underlying stock price vs option strike, not option premium vs strike. *(Completed 2026-04-03: `applyPortfolioFilters` enforces near-money threshold logic and configurable `%` bound; regression coverage in `frontend/src/components/portfolioFilters.test.js`.)*
        - [x] **Underlying STK inclusion for option filters**: When option-focused filters such as `Expiring` or `Near Money` are active, include the matching underlying stock row for each visible option group, but do not show stock rows that do not belong to one of the filtered option groups. *(Completed 2026-04-03: option-focused filter mode now includes only matching `(account, underlying)` STK rows and excludes unrelated stocks; regression coverage in `frontend/src/components/portfolioFilters.test.js`.)*
    - [x] **Show "STK ?" Filter**: Add a dedicated `Show "STK ?"` portfolio filter/toggle that is checked by default. When checked, stock rows should be shown anywhere the related option group is shown; when unchecked, users may hide stock rows from the portfolio grid and related filtered views.
        - [x] **portfolio-show-stk-001**: Default state is checked on `?view=PORTFOLIO` so STK rows are visible unless the user explicitly turns them off.
        - [x] **portfolio-show-stk-002**: The `Show "STK ?"` toggle must combine with `Expiring`, `Near Money`, coverage status, and account filters using `AND` semantics, without breaking the inclusion of matching underlying rows for option-driven views.
        - [x] **portfolio-show-stk-003**: When `Show "STK ?"` is checked, any filtered option result set that is shown in the grid must also include its related underlying STK row in the same account/underlying group.
        - [x] **portfolio-show-stk-004**: When `Show "STK ?"` is unchecked, stock rows should be suppressed from the visible portfolio grid even if related options remain visible, unless a future requirement explicitly overrides that behavior.
    - [x] **Last Price**: Sort and filter by last price. *(Completed 2026-04-03: added explicit toolbar `Min/Max` Last Price controls in `PortfolioGrid.jsx`; filtering is enforced in shared `applyPortfolioFilters` logic with regression tests in `frontend/src/components/portfolioFilters.test.js`.)*
        - [x] **portfolio-last-price-001**: Portfolio grid supports sorting by `Price` (`market_price`) via the column header.
        - [x] **portfolio-last-price-002**: Add explicit `Price Min/Max` (or `>= / <=`) toolbar controls so users can filter the visible portfolio rows by last price, with regression tests for combined filter behavior.
    - [X] **Account Filter**: Portfolio list Sort and filter by account #. 
    - [x] **Portfolio Row Counter**: Portfolio toolbar should display the current visible row count after all active filters are applied so the operator can quickly see how narrow the focus set is. *(Completed 2026-04-02: row counter now bound to final post-filter visible row set; regression utility tests added in `frontend/src/components/portfolioPresentation.test.js`.)*
    - [x] **Uncovered Filter**: Portfolio show STK & OPTS for all STK that do NOT have FULLY covered positions (ie: # of shares != # of contracts*100). the link to "Uncovered filter" (existing) doesn't work. It should ONLY filter STKs that accountID.STK(qty)==accountID.OPT(qty)*100 by  NOTE:  
            Covered     : account.STK == abs(account.OPT_SHORT*100) only absolute value of qty of shorts 
            Uncovered   : account.STK > abs(account.OPT_SHORT*100) only absolute value of qty of shorts
            Naked       : account.STK < abs(account.OPT_SHORT*100) only absolute value of qty of shorts 
    - [x]  **Covered/Uncovered/Naked Filter**: The Covered/Uncovered status should be uniquely filterable by the 3 status values.  No filter (aka: ALL) should be default value, uncovered is NOT the same as NAKED! Coverage selection remains mutually exclusive, but it must combine with `Expiring`, `Near Money`, and `Account` filters using `AND` semantics. Reference: `docs/coverage_filtering.md`. *(Completed 2026-04-02: strict coverage matching hardened and case-insensitive regression added in `frontend/src/components/portfolioFilters.test.js`.)*
    - [x] **Portfolio Coverage Status Regression**: Re-verify the `?view=PORTFOLIO` coverage-status contract after later portfolio/live-grid changes so prior fixes do not silently regress. Reference: `docs/plans/implementation_plan-20260328-portfolio_coverage_refactor.md`, `docs/learning/bad-trade-heuristics.md`. *(Re-verified 2026-04-02 via `tests/test_coverage_status.py`, `tests/test_portfolio_enrichment.py`, and `tests/test_portfolio_holdings_normalization.py`.)*
        - [x] **portfolio-coverage-001**: Coverage status must be calculated at `(account, underlying)` granularity using absolute short call quantity only: `Covered = STK_qty == abs(short_call_qty * 100)`, `Uncovered = STK_qty > abs(short_call_qty * 100)`, `Naked = STK_qty < abs(short_call_qty * 100)`. *(Verified 2026-04-02: `_resolve_coverage_status` in `routes.py` uses `(account_id, und)` key with `abs(qty) * multiplier` accumulation. Unit tests in `tests/test_coverage_status.py`.)*
        - [x] **portfolio-coverage-002**: User case regression: account `U110638` holding AMD with `200` shares and `-2` short call contracts must render as `Covered`, not `Uncovered`. *(Verified 2026-04-02: `test_amd_regression_covered` in `tests/test_coverage_status.py` asserts `_resolve_coverage_status(200, 200) == "Covered"`.)*
        - [x] **portfolio-coverage-003**: When a `(account, underlying)` group resolves to `Covered`, the underlying STK row and each related short-call row shown in the portfolio grid must display the same `Covered` status. *(Verified 2026-04-02: `TestCoverageGroupConsistency` in `tests/test_coverage_status.py` confirms both rows get same status since both use the identical shared `(account, underlying)` accumulator.)*
        - [x] **portfolio-coverage-004**: Add or refresh regression tests for the exact covered/uncovered/naked scenarios used by the portfolio filters so merged-source or row-shape changes cannot re-break coverage classification. *(Completed 2026-04-02: added explicit `(account, underlying)` AMD `200` shares with `-2` short calls regression in `tests/test_portfolio_enrichment.py`.)*
        - [x] **portfolio-coverage-005**: Flat rows (`quantity == 0`) must not be labeled `Covered`, `Uncovered`, or `Naked`; set `coverage_status` to blank for those rows so coverage focus filters only match active positions.
    - [/] **Pending Order Aware Coverage / Roll State**: The portfolio must show not only the current covered/uncovered/naked state, but also whether there are pending orders that would fill uncovered shares, buy back covered calls, or roll an existing covered-call position. Reference: `docs/features/portfolio_pending_order_coverage.md`.
        - [x] **portfolio-pending-coverage-001**: Keep `coverage_status` as the current filled-position truth based only on actual STK and OPT positions. Pending orders must not overwrite this current-state field.
        - [x] **portfolio-pending-coverage-002**: Add a second derived field such as `pending_coverage_effect` or `coverage_state_if_filled` that summarizes what active working orders would do for the `(account, underlying)` group. Minimum states: `none`, `covering_uncovered`, `buying_to_close`, `rolling`, `increasing_naked_risk`, `unknown`.
        - [x] **portfolio-pending-coverage-003**: For uncovered stock, detect pending short-call sell orders that would reduce or eliminate the uncovered share gap if filled. The UI should show shares currently uncovered, shares covered now, and shares proposed to be covered by working orders.
        - [x] **portfolio-pending-coverage-004**: For currently covered positions, detect pending `BUY` orders on the short call leg that represent buy-to-close behavior, plus paired or related sell-to-open replacement orders that represent a roll when that intent can be inferred reliably.
        - [x] **portfolio-pending-coverage-005**: If roll intent cannot be proven from the order data, the UI should show separate pending-leg facts rather than incorrectly labeling the position as a roll. Truthful partial visibility is better than a false roll classification.
        - [x] **portfolio-pending-coverage-006**: Portfolio rows should expose both current coverage state and pending-order intent at the `(account, underlying)` group level for the stock row and all related option rows. Detail-drawer UI follow-up remains open.
        - [x] **portfolio-pending-coverage-007**: Add focus filters or badges for `Pending Cover`, `Pending BTC`, and `Pending Roll` so the operator can quickly find actionable positions in `?view=PORTFOLIO`.
        - [x] **portfolio-pending-coverage-008**: Add or refresh regression coverage for representative cases: uncovered shares with one pending short call sell order, covered call with pending buy-to-close only, covered call with buy-to-close plus replacement short call roll, and ambiguous order sets that must remain `unknown`.
        - [x] **portfolio-pending-coverage-009**: Add a dedicated `Pending BTC` grid column pinned at the far-right and shorten the column heading to a compact label (`P.BTC`) so it consumes less horizontal space while keeping buy-to-close intent visible.
    - [X] **Options Due in X Days**: Modify the "Expiring (<6D)" filter to allow user changeable control/field for specifying the days to expiration. Expiring <## field. 
    - [x] **Export**: Export current view of portfolio to CSV (inclusive of filters). *(Completed 2026-04-03: all export requirements `portfolio-export-001..004` are now marked complete and test-backed.)*
        - [x] **portfolio-export-001**: CSV export must use the same final visible-row set as the current `?view=PORTFOLIO` grid after all active filters and toggles are applied.
        - [x] **portfolio-export-002**: When option rows are exported with `Show "STK ?"` checked, the export must also include the corresponding STK row for each exported option group so the CSV does not omit the underlying stock context.
        - [x] **portfolio-export-003**: When `Show "STK ?"` is unchecked, the CSV export should omit STK rows in the same way the grid omits them.
        - [x] **portfolio-export-004**: Add or refresh regression coverage to verify portfolio CSV export stays aligned with the on-screen filtered row set, including `Expiring`, `Near Money`, coverage status, account, and `Show "STK ?"` combinations. *(Completed 2026-04-02: frontend filter/export alignment tests added in `frontend/src/components/portfolioFilters.test.js` for both `showStocks=true` and `showStocks=false` with combined filter logic.)*
    - [x] **LINK to Stock Analysis Detail**: Portfolio Page quick link next to ticker and existing Google / Yahoo links should use the external-link arrow-out-of-box glyph for Stock Analysis detail, not a `D` text label. Improve the glyph color/contrast so it reads clearly against the background, and keep using the same shared modal detail window logic used from the ticker analysis list. *(Completed 2026-04-03: ticker cell uses `ExternalLink` glyph and shared modal-open click flow in `PortfolioGrid.jsx`.)*
    - [x] **Ticker Column Width / 3 Link Fit**: Make the default ticker column width on grid views wide enough for long OPT ticker names plus the 3 ticker links (Google, Yahoo, Stock Analysis detail) so users do not need to manually drag the column wider. Prevent truncation that hides contract identity or link actions. *(Completed 2026-04-03: widened ticker columns for Portfolio/Trades grid defaults with quick-link fit behavior.)*
- [x] **Portfolio View — TWS Live Grid Regression Fixes**: Review and fix the 2026-03-31 `?view=PORTFOLIO` regressions introduced or exposed during TWS realtime integration. Reference: `docs/features/portfolio_tws_live_grid_regressions_20260331.md`. Tracked as `portfolio-live-grid-undefined-values` bug in Section 0. *(Completed 2026-04-02: `001..006` locked with backend row-shape normalization + frontend presentation helpers + regression tests.)*
    - [x] **portfolio-live-grid-001**: Price, Value, Basis, and Unrealized PnL must not render the JavaScript literal `undefined`. If live fields are absent, use explicit fallback/null rendering rather than broken currency text. *(Completed 2026-04-02: shared formatter guards verified in `frontend/src/components/portfolioGridFormatters.test.js`.)*
    - [x] **portfolio-live-grid-002**: `% NAV` must not render `NaN%`. Guard row-level percentage math when NAV, market value, or live fields are missing or zero. *(Completed 2026-04-02: percent formatter NaN/undefined guard regression coverage added in `frontend/src/components/portfolioGridFormatters.test.js`.)*
    - [x] **portfolio-live-grid-003**: Restore correct `Type` detection and display for `STK` vs `OPT` in the portfolio grid when records come from Flex, TWS, or merged sources. *(Completed 2026-04-02: canonical type normalization consolidated in `frontend/src/components/portfolioPresentation.js` and used by `PortfolioGrid`.)*
    - [x] **portfolio-live-grid-004**: Restore option contract description details in the portfolio grid so option rows show meaningful contract metadata instead of partial or blank identifiers. *(Completed 2026-04-02: backend now guarantees `display_symbol`/`description` fallback in `_normalize_portfolio_row`.)*
    - [x] **portfolio-live-grid-005**: Normalize the portfolio row view-model so TWS/live records and Flex/EOD records expose the same field names for price, market value, cost basis, unrealized PnL, `% NAV`, `secType`, and description before rendering. *(Completed 2026-04-02: additional camelCase+legacy alias normalization added in `routes.py`.)*
    - [x] **portfolio-live-grid-006**: Add regression coverage for merged-source portfolio rows so previous fixes like the older Type-column fallback do not silently break when realtime data is present. *(Completed 2026-04-02: coverage in `tests/test_portfolio_holdings_normalization.py`, `tests/test_portfolio_enrichment.py`, and `frontend/src/components/portfolioPresentation.test.js`.)*

### Analysis & Signals
- [ ] **"Juicy" Opportunity Finder**:
    - [ ] **Juicy Opportunity Collection**: Implement full lifecycle tracking for detected opportunities. Allows complex long running processes to be only run once and the results persisted to be used for other features. 
        - [x] **Data Schema**: Define `JuicyOpportunity` model (Symbol, Timestamp, Context: {Price, IV, Greeks}, Proposal, Trigger Source).
        - [ ] **Persistence**: Store opportunities in MongoDB (`opportunities` collection) for historical analysis.
        - [ ] **Outcome Tracking (Truth Engine)**:
            - [ ] **Requirement**: Automated tracker that monitors the specific option/stock for the duration of the proposed trade.
            - [ ] **Metrics**: Max Profit (MFE), Max Loss (MAE), Days to Profit, Expiration Value.
            - [ ] **Reference**: See [Opportunity Persistence & Grading](learning/opportunity-persistence-and-grading.md).
        - [ ] **Grading Engine**: Scheduled job to close and grade opportunities (Win/Loss, ROI/Day) based on market data.
        - [ ] **Signal Correlation**: Dashboard to analyze Hit Rate by Signal Source (e.g., "Do Gap Ups work?"). 
        - [ ] **X-DTE options UI**: Only show the DTE<7 list of options so they can be evaluated for rolling, holding, waiting, or closing. Leave space for showing greeks, probability, payouts, Returns, yields, LT vs ST P&L, create UX for showing opportunties available for rolling, holding, waiting, or closing. See [Implementation Plan](plans/implementation_plan-20260203-xdte_autoroll.md).
        - [ ] **Auto-Roll Evaluation**: Automatically analyze rolling opportunities for these positions (e.g., Roll to next week or month if covered call is ITM). See [Implementation Plan](plans/implementation_plan-20260203-xdte_autoroll.md).
        - [x] **Auto-Roll Fixes**: The roll doesn't show the yield and the return. It's unclear what the original ticker OPT details are it's MSFT put or call. Original strike price is unknown. Time of the original contract and return / yield is unknow. What about the whole sequence of that buy and sell? What part makes money? Under what scenario (price change Up/Down, time change, yield change) does it make money? 
        - [x] **Auto-Roll Fixes**: What does the SELECT button do? **Definition**: Clicking "Select" logs the chosen roll strategy (Buy to Close Current + Sell to Open New) and provides a "Success" toast notification. Future state will persist this to a Trade Plan or trigger an IBKR Order ticket.
        - [x] **Auto-Roll Fixes**: The "Dividend Capture Opportunities" button is huge and empty which is not a good user experience.
        - [x] **Auto-Roll Fixes**: After clicking on a roll there is spinner as it's thinking. Do these Smart Roll Analysis get saved somewhere?  
        - [x] **Auto-Roll Fixes**: No suitable rolls found for this position. Misses the point, WAIT, HOLD, or CLOSE. Are options also? If there are no suitable rolls found for this position, is the XDTE only offer a roll? 
        - [/] **Smart Roll Analysis**: analysis misses UP value for the roll. Add info regarding UP Return/Yield and Tot: yield. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
        - [x] **UI fixes**: My portfolio is missing Type column data for each row. Originally covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md). Regressed again in the 2026-03-31 TWS live portfolio grid path; also tracked under `portfolio-live-grid-003` / `portfolio-live-grid-006`.
        - [/] **UI fixes**: Trades view is shows an obvious OPT trade as STK trade? It should show open or close, BUY or SELL, if close show the profit yield. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
        - [/] **UI fixes**: My Portfolio the XDTE boxes only use 1/2 the width of the available space. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
        - [/] **UI fixes**: The XDTE still shows 2D as the i assume the number of days to expiration even though it's 4D. Debug why this is happening. ref docs/learning/dte-calculation-standards.md. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
        - [x] **Scheduler Integration**: Scans scheduled every 30 mins (Market Hours) and 1 hr Pre/Post-Market.
        - [x] **UI Scheduler Integration BUG FIX**: Fixed x-div signal not firing. Expanded lookahead window to 0-30 days (was 2-14) and fixed Scheduler method call typo. 
        - [/] **Recommendation Database**: Is there a local mongo persistent database of all signals triggered, when they were triggered what was their score so that any and ALL relevant data is available for analysis? Make sure that All Rolls, xdivs, and any top 10 scored recommendation is saved for analysis, so that later scores can be calculated based on the success and outcomes of these recommendations, no matter if I chose to trade on them or not. 
        - [ ] **xdiv signal**: widget should scan ALL/any stocks upcoming dividend x-div date in the analysis ticker list and not just the current portfolio stocks.  
        - [ ] **1D NAV UI**: shows The 1 day NAV is showing 0, there something broken with the logic. 
        - [x] **UI Performance**: UI components (e.g., Dividend Capture) must read from DB persistence, NOT trigger blocking live scans.  
    - [ ] **Heuristic Checklist for Your Dashboard**; Pattern, Detection Logic, Risk Type referenced in docs/learning/bad-trade-heuristics.md
    - [x] **Opportunity Signals**: Detect and alert on uncovered stock positions (gap shares) suitable for covered calls (displayed as "Opp Block" in Portfolio view).
    - [x] **Bug issue**: MRVL Gap 500 Shares, Trend UP (+0.12%) but it's not up in recent trading. **Fixed**: Corrected parsing of "1D % Change" in OptionsAnalyzer and fixed scoring logic for trend.
    - [x] **Opportunity Scoring Rubric**: See [Opportunity Scoring](learning/opportunity-scoring.md). Defines the 0-100 rating scale and factors (IV, Trend, Liquidity). 
    - [ ] **juicy-opportunity-refresh-job-001**: Add a dedicated scheduler job path for Juicy opportunity refresh (manual enqueue + periodic run). Job should reevaluate tracked analysis tickers and upsert only changed/new/better-scored opportunities with `last_scored_at` timestamp.
    - [ ] **juicy-opportunity-refresh-job-002**: Refresh job source precedence: use TWS realtime where available for live option/underlying inputs, otherwise yfinance fallback, and record `data_source` used per opportunity snapshot.
    - [ ] **juicy-opportunity-refresh-job-003**: Persist refresh-run audit documents (queued/start/end/status/row counts/errors) so UI and operators can diagnose stale Juicy tables quickly.
    - [x] **Smart Roll / Diagonal Assistant**: Analyze existing short calls expiring within X days to find optimal rolling strategies (Calendar/Diagonal Spreads).
        - [ ] **Goal**: Optimize for short duration and favorable Return/Yield, prioritizing trades that result in a net credit or "decent return" even when buying back the existing position.
        - [x] **Greeks Data Ingestion (Analysis)**: Determined that `yfinance` does not provide Greeks. Created [Greeks Ingestion Strategy](../docs/learning/greeks-data-ingestion.md) detailing how to calculate them using Black-Scholes (`py_vollib`).
        - [x] **Greeks Implementation**:
            - [x] **Dependencies**: Add `py_vollib_vectorized` to `requirements.txt`.
            - [x] **Calculator Util**: Create `app/utils/greeks_calculator.py` to process DataFrames.
            - [x] **Service Update**: Integrate calculator into `RollService` to enrich option chains with Delta/Gamma/Theta.
        - [/] **X-DIV Strategy**: Get data for ticker's x-div dates and premiums for calls and puts and scoring for rolls, diagonals, and other strategies.
            - [x] **Research**: See [X-DIV Rolling Strategy](../docs/learning/x-div-rolling.md). Defines Assignment Risk heuristics.
            - [x] **Backend**: Fetch `exDividendDate` and `dividendRate` from `yfinance`.
            - [x] **Scoring**: Implement "Dividend Assignment Risk" penalty in `score_roll` (Extrinsic value < Dividend).
            - [x] **Dividend Capture**: (Buy-Write) strategies specifically in the Opportunity Finder? YES update this as requirement. Implemented `DividendScanner`.
            - [x] **x-div**: create a new folder xdivs top level of workspace, docker map this folder to the development folder for persistance. Save all x-div .ics files here, with daily name stamps. If it already exists then it doesn't need to be created again.  
            - [x] **x-div**: Have this file be able to be download this physical file like the .xlsx file is `/api/calendar/dividends.ics`.
            - [/] **events**: Find all corporate events (Earnings, x-div, etc) for all the tickers being tracked and add them to calendar.ics download file out 90 days and make this a settings configurable number of days calendar. The calendar should have a link to the news feed or notice or corporate website for that event x-div should have a link to yahoo finace that ticker.  
            - [x] **events**: Only search STK tickers or find the underlying OPT's STK tickers. **bug fix** add this bug fix feeature to xdiv and events scanner to filter only STKs not to search for options: from logs:  quote.py-yfinance-_fetch - ERROR - HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: AMD   260220C00235000"}}}
            - [/] **events**: Add these to the database per the *News Feeds* backend database. Maintain historical record of all events for lookup?
            - [x] **events**: Create ical calennder URL end point so another calendar can subscribe the combined xdiv and corporate events juicy calendar. *(Completed 2026-04-03: added stable alias endpoint `/api/calendar/juicy.ics` alongside `/api/calendar/dividends.ics`; backend regression coverage in `tests/test_calendar.py`.)*
            - [x] **x-div**: Change the Dividend Capture to be the same size button as the "Smart Roll" opportunity button (use a differnt color motif to differentiate) and have a click link to pop a new window to show the details of the ticker, xdiv date, dividend amount, and the recommended strike price and premium to sell clean simple summary list,  Using the Smart Roll Analysis window as a template, allow the user to select and evaluate the Dividend Capture strategy Analysis. There should be an intermediate screen that lists out all the dividend opportunties by date, account, ticker, Clicking on a specific dividend opportunity should bring up the analysis window for that specific dividend opportunity. 
            * [x] **Analysis Selection Template**: Given that there will be multiple strategies each should use the same look and feel for the analysis window for selection so we don't have to recode the selection window for each Opportunity type.
            * [x] **Opportunity Widgets**: Keep compact so they fit 8 wide on the grid. Color code the different buttons based on the strategy type.
        - [ ] **Scoring**: Smart Roll Strategy - Roll UP Factor in underlying stock profit (increase in strike width), cost to close, and premiums of new strikes. When doing a Roll, consider paying for a better UP position and factor in the momentum effect of going too far OUT on a stock trending UP (velocity of stock). Shorter term rolls (calculate yeild off of total improvement including STK UP value and OPT Premiums). Yield is different from returns (annualized *365/Days to event)
        - [x] **Dividend Feed UI**: Display a **sortable list** with **one row per Ticker**. Columns: Date, Ticker, **aggregated Accounts & Qty** (e.g., "Main: 100, IRA: 50"), Current Price, Predicted Price (Markov), Analyst Target, Dividend Amount, Return, Yield, Days to Dividend. 
        - [x] **Dividend Feed**: Implement finance.yahoo link around the ticker symbol in a new tab. *(Completed 2026-04-03: ticker link opens `https://finance.yahoo.com/quote/{TICKER}` in `DividendListModal.jsx`.)*
        - [x] **Dividend Feed**: *bug* the Holdings, Predicted Price, Target fields are empty. Is there a test for this?  The Returns field is meaningless cause it's basically the dividend amount. *(Completed 2026-04-03: UI fallback rendering remains in `frontend/src/components/dividendPresentation.js`; return semantics now represent projected price move + dividend cash into ex-date in `app/services/dividend_scanner.py`; regression coverage in `tests/test_dividend_feed.py` and `frontend/src/components/dividendPresentation.test.js`.)*
        - [/] **Dividend Capture Analysis**: Should show each of the accounts, Qty held, any open option positions (calls and puts qty -neg is sold, vs + is bought) 
        - [/] **Dividend Capture UI**: Find and evaluate all BUY/SELL Call strategies around the xdiv date list them out, should show any other option opportunities available (roll etc). 
        # TODO: Smart Roll Analysis
        - [ ] **NEXT STEP**: Implement "Momentum Trigger" in `RollService.score_roll`. Adjust score based on `1D % Change` vs `DTE` (See [Smart Roll Logic](learning/smart-roll-diagonal.md#b-dynamic-dte-scaling-momentum-trigger)).
        - [ ] **Smart Roll Gamma Penalty**: Implement "Gamma Penalty" for DTE < 2 and Moneyness > 0.98.
        - [ ] **Smart Roll Reset Protocol**: Implement "Reset Protocol" (Defense Buy-Back) to suggest closing instead of rolling in bearish trends.
        - [ ] **Smart Roll Buy Up Protocol**: Consider paying for a better UP position and factor in the momentum effect of going too far OUT on a stock trending UP (velocity of stock). Logic being what's the cost of buying a better strike price coverting ST OPT profits to LT STK gains.  
        - [x] **Implementation Plan**: All above "NEXT STEP" items are covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).

        - [x] **strategy**: Find suitable Roll Calendar/Diagonal with favorable Return and Yield. Consider position move to more profit (unrealized stock gain) vs cost of buyback. Prefer near 0DTE or short term if profitable, incorporate all the strategies available to make recommendations or opportunities on the portfolio.
        - [x] **Add to UI**: Incorporate into the app.
            - [x] **Smart Roll Widget**: In `TickerModal` (for held positions) and `PortfolioGrid` (overview). Display score, net credit, and "Dividend Risk" warnings.
            - [x] **Dividend Capture List**: New section in `Dashboard` or modal to display logic from `/api/analysis/dividend-capture`.
            - [x] **Calendar Export**: Button in `PortfolioGrid` (via Dashboard Dropdown) to download `.ics` file.
        - [x] **Smart Roll Strategy**: See [Smart Roll & Diagonal Strategy](learning/smart-roll-diagonal.md). Defines heuristics for Short Duration (<10 days), Credit Priority, and Strike Improvement.
        - [x] **Smart Roll Strategy**: See [Smart Roll & Diagonal Strategy](learning/smart-roll-diagonal.md). Update algo and heuristics to incorporate UP strategy benefit of the STK increase in return and yield.  Add UP value to scoring algo also  if it's not already there. Record in dB STK Return & Yield, Total Return &Yield (ie: OPT return & yield) 
    - [x] Screen for call buying opportunities (momentum).
    - [ ] Strategy: Use "Juicy Calls" premium to fund downward protection (puts) or long calls. Add this to the opportunity finder section of the ticker modal and the portfolio view.
    - [x] **Juicy Thresholds**: See [Juicy Thresholds](learning/juicy-thresholds.md). Defines quantitative limits (IV Rank > 50, Delta 0.3-0.4).
    - [x] Implement Scanners/Screeners module in Python.
- [ ] **Targeting Logic**: Integrate Macro trends and News events into the analysis and portfolio views.
    - [x] **News Feeds**: Integrate external News API (e.g., NewsAPI.org). *Backend Implemented*
    - [x] **News Feeds**: Build a News Aggregator to fetch news events and store them in a database. *Backend Implemented*
    - [/] **News headlines and Senitiments**: stored with Logic/Reasoning. *UI Pending*. similar to "Sea Limited (SE)..."
        - [x] **Data Structure**: Enforce strict JSON output with `logic`, `reasoning`, `impact_window`, and `opportunity_score`.
        - [x] **Validation**: Ensure "Sea Limited" example case is strictly reproducible. 
    - [x] **Sentiment**: write a sentiment analysis module using `transformers` or `nltk`. 
        - [x] **Heuristics**: Implement "Logic Check" (Stage 1) to assign Short/Long term impact based on keywords.
    - [x] **Sentiment**: write a learning features document for sentiment and headlines  .agent/workflows/learing-opportunity.md Same or extra doc as here: @features-requirements.md#L163 
    - [x] Fetch Macro indicators (Fred API). *Backend Implemented*
    - [/] Create "Impact Score" for news events on portfolio tickers. *Logic Implemented, UI Pending*
        - [ ] **Research**: Evaluate X (Twitter) API v2 Basic Tier (~$100/mo) vs Free Limits for "Alpha Lists".
        - [ ] **Research**: Investigate Yahoo Scout integration (Scraping vs User Manual Copy/Paste).
    - [x] **Learning Opportunity**: - using the  .agent/workflows/learing-opportunity.md write a learning doc about how to LMM and target macro trends and news events in our trading. 
- [/] **Markov Chains**: Implement Markov Chains for signal generation and proposed strategies like rolls vs holding for a given OPT and it's underlying stock. 
    - [x] Research `markovify` or `pykalman` libraries.
    - [x] Prototype Mean Reversion and Trend Following models using Kalman.
    - [x] **Learning Opportunity**: - using the  .agent/workflows/learing-opportunity.md write a learning doc about how to use Markov Chains for signal generation and proposed strategies like rolls vs holding for a given OPT and it's underlying stock.  How does this work with Kalman filters, pros and cons, what's better for what scenario.  How to use this to generate signals for the portfolio.  Recommend next steps and update feature-requirements.md lists for Markov chains as needed. See [Markov Chains & Kalman Signals](learning/markov-chains-signals.md).
    - [x] **Infrastrucutre**: Implement Backend Service and API.
        - [x] Create `SignalService` with Kalman trend smoothing and Markov state transitions.
        - [x] Expose `GET /api/analysis/signals/{ticker}` endpoint.
    - [/] **NEXT STEP**: Integrate experimental signals into **Smart Roll** assistant to improve "Roll vs Hold" advice. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
    - [/] **NEXT STEP**: Markov Chains predictions stocks, Options,  signals in Frontend **Ticker Modal** for visual analysis. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
    - [/] **NEXT STEP**: Markov Chains in the scoring algo. Covered in [Smart Roll & Markov Integration Plan](plans/implementation_plan-20260203-smart_roll_markov.md).
    - [ ] **NEXT STEP**: Create a new section in the **Dashboard** to display signals for the portfolio.

- [x] **Kalman Filters Research**: See [Kalman Filters in Trading](learning/kalman-filters.md). Explains Mean Reversion and Trend Following applications.
- [ ] **Kalman Filters**: Implement Kalman filters for signal generation. 
    - [ ] Research `filterpy` or `pykalman` libraries.
    - [ ] Prototype Mean Reversion and Trend Following models using Kalman.
    - [x] **Kalman Filters Research**: See [Kalman Filters in Trading](learning/kalman-filters.md). Explains Mean Reversion and Trend Following applications.
- [/] **PRICE ACTION**: Implement Price Action analysis. Integrate into Portfolio Management analysis views.
    - [x] **Analysis Plan**: See [Implementation Plan](plans/implementation_plan-20260202-price-action.md) and [Concepts](learning/price-action-concepts.md).
    - [/] Understand Market Movement 
    - [/] Market Structure (HH, HL, LH, LL) - *Using ZigZag Algorithm (n=5)*
    - [/] Break of Structure (BOS) - *Body Candle Close*
    - [/] Supply & Demand zones - *Fair Value Gaps (FVG)*
    - [/] Order Blocks (base) - *Validated by FVG*
    - [ ] Goal: Know 'why' price moves
- [ ] **Stock Research**: Implement Stock Research module using Gemini AI.
    - [ ] **Business Understanding**: Prompt Gemini to explain the business model, problem solved, and customer value proposition.
    - [ ] **Revenue Breakdown**: Analyze revenue streams, segment growth, and product/customer dependencies.
    - [ ] **Industry Context**: Evaluate industry maturity, long-term trends, and market dynamics.
    - [ ] **Competitive Landscape**: Benchmark against competitors on pricing power, moats, and product strength.
    - [ ] **Financial Quality**: Assess revenue consistency, margins, debt levels, and cash flow strength.
    - [ ] **Risk & Downside**: Identify critical business, financial, and regulatory risks.
    - [ ] **Management & Execution**: Evaluate historical execution and alignment with long-term shareholders.
    - [ ] **Bull vs Bear Scenario**: Generate fundamental-based scenarios for the next 3-5 years.
    - [ ] **Valuation Thinking**: Determine key valuation drivers and assumptions for multiple expansion/contraction.
    - [ ] **Long-Term Thesis**: Synthesize a comprehensive investment thesis with clear "signs of being wrong."
    - [ ] **Spread Drag**: (Ask - Bid) / Mid > 0.05  Execution
    - [ ] **Volatility Crush**: Entry IV > 80th Percentile Tactical
    - [ ] **Zombie Trade**: Days Held > 45 AND ROI < T-Bill Rate Opportunity Cost
    - [ ] **Size Violation**: Trade Risk > 2% of Net Liquidity Account Survival

- [ ] **Predictions**: Use LMM or Markov Chains to predict future stock prices and options prices.  Use this to generate signals for the portfolio.  Recommend next steps and update feature-requirements.md lists for Markov chains as needed.
- [x] **Future LLM**: Prepare hook for Gemini/LLM to generate natural language `reasoning`. Implemented `GeminiService` and `GOOGLE_API_KEY` config.
- [/] **Trading Agent**: Update using my Gemini pro account with api or link to gemini with the context of the question (GIVEN: STX qty, cost basis and OPT or situation what is the best trade based on a certain pattern of strategies availables and have it evaluate the risk and reward, news, etc for that scenario maybe even in a seperate tab/window Update See [Agent Frameworks](learning/agent-frameworks.md)
- [x] **Trading Agent**: UI create a link on TYPE column of the My Portfolio detials for each ticker item STK or OPT that opens a new tab/window with the trading agent interface passing all the relevant information. Implemented in `PortfolioGrid.jsx`.
 
### Strategy & Backtesting
- [ ] **Backtesting Engine**:
    - [ ] Ability to "back play" strategies using historical IBKR data.
    - [ ] Evaluate libraries: Zipline, VectorBT, or custom.
    - [x] **Engine Selection**: See [Backtesting Engines](learning/backtesting-engines.md). Compares Vectorized vs Event-Driven (Recommended). 
    - [ ] Create Data Ingestion for OHLCV bars (1-min, 1-hour, 1-day).
- [ ] **Metric Stack**: Implement standard metrics: Sharpe, Sortino, MaxDD, Hit-rate, Turnover.
    - [ ] Implement `empyrical` or equivalent library for standardized metric calculation.
- [ ] **Personal Trading History**:
    - [ ] Build history of Ken's previous trades.
    - [ ] Analyze performance of past trades to derive a personalized strategy.
    - [ ] **RAG for Trading History**: Chat with past trading data.
    - [ ] Implement CSV/Excel importer for non-IBKR/Manual trade logs.
    - [ ] Create "Journal" dashboard to annotate past trades with emotional state/reasoning.

### ML in the Loop (8-Step Flow)
- [ ] **Universe Selection**: Define the pool of tradeable assets. Find new juicy fruit candidates based on macro trends, news events, and quant analysis.
    - [ ] Implement Liquidity Filters (Volume, Open Interest).
    - [ ] Implement Sector/Industry filtering.
- [ ] **Feature Engineering**: Momentum, Quality, Volatility factors.
    - [ ] Create `FeatureStore` module (TA-Lib integration).
    - [ ] Implement "Juicy" specific factors (IV/HV ratio, etc).
- [ ] **Time-Series CV**: rigorous cross-validation without look-ahead bias (leakage).
    - [ ] Implement Purged K-Fold Cross Validation.
- [ ] **Model Training**: Implementation (e.g., XGBoost, Scikit-learn).
    - [ ] Create Training Pipeline (GridSearch/Optuna).
- [ ] **Validation**: IC (Information Coefficient), Feature Importance.
- [ ] **Signal Creation**: Generating raw scores.
- [ ] **Portfolio Construction**: Optimization based on signals.

---

## 4. Dashboard & UX Features 
**Owner:** Frontend Team | **Goal:** A "Wow" factor UI with actionable data.

### Navigation & Workspace
- [ ] **Top Navigation — Juicys Workspace**:
    - [x] **juicys-nav-001**: Add a new top-level navigation tab labeled `Juicys` in the main dashboard nav (alongside Analysis/My Portfolio/Trade History/Orders). *(Completed 2026-04-07: Dashboard top-nav includes `Juicys` route/state.)*
    - [x] **juicys-nav-002**: Route `Juicys` to a dedicated spreadsheet-style workspace showing all tracked analysis tickers and their current Juicy opportunities from Mongo persistence (not live-only ephemeral results). *(Completed 2026-04-07: `GET /api/juicys` DB-first rows rendered in `JuicysGrid`.)*
    - [x] **juicys-nav-003**: Workspace defaults to "Juicy main" view and displays all Juicy items; include filter presets for "Juicy Fruit Options" and "Hot PUTS on down market days". *(Completed 2026-04-07: workspace loads full juicy set with `Juicy Fruit Options` / `Hot PUTS` presets.)*
    - [x] **juicys-nav-004**: Juicys grid should support column sorting/filtering/search with ticker-first layout consistent with existing data tables. *(Completed 2026-04-07: ag-Grid sortable/filterable columns with ticker-leading layout.)*
    - [x] **juicys-nav-005**: Add workspace `Refresh` action that schedules the Juicy refresh job and shows queue/freshness status instead of blocking on synchronous fetches. *(Completed 2026-04-07: `Refresh` calls `POST /api/juicys/refresh` queue path and then reloads persisted rows.)*
    - [ ] **juicys-nav-006**: Provide spreadsheet download/export for currently filtered Juicys rows (same expectation as Analysis table exports).
    - [x] **juicys-nav-007**: Create and maintain feature detail doc [Juicys Navigation + Optimizer Workspace](features/juicys_navigation_optimizer_workspace.md) as the implementation contract. *(Completed 2026-04-07; updated 2026-04-07 with chain-depth + liquidity + short-DTE contract.)*

### Visualizations
- [ ] **Interactive Graphs**:
    - [ ] Stock Price vs Moving Averages (interactive, zoomable).
    - [ ] Local graphs for private portfolio performance.
    - [ ] Evaluate Charting Libraries (Recharts, Chart.js, Plotly).
    - [ ] **Performance**: Do you prefer performance (Canvas - good for high frequency) or interactivity (SVG - good for tooltips/css)? generally svg is better for interactivity for a small user base, but even for just me not too slow.
- [ ] **Yield Analysis**: Visuals for Yield vs Cost Basis vs ROI.
    - [ ] Implement Heatmap visualization for Option Greeks.
- [ ] **Mini Sparklines**: Add price trend sparklines directly into the Analysis and Portfolio table rows for rapid visual trend assessments (turning raw numbers into immediate insight).

### UX Performance & Polish
- [ ] **Perceived Performance**:
    - [ ] **Skeleton Loading States**: Implement skeleton row/grid implementations for ag-Grid and Modal tabs to provide immediate structural feedback while data fetches, avoiding abrupt "loading spinner" walls.
    - [ ] **Sync Progress Animation**: Replace the static "TWS Live" indicator with a subtle, non-intrusive "Syncing..." micro-animation / progress bar when background fetches execute.
- [ ] **Actionable Interaction & Spatial Optimization**:
    - [ ] **"One-Click Roll" Acceleration**: Make the "Smart Rolls" suggestions explicitly actionable; clicking a roll suggestion should pre-populate a sliding order-ticket drawer.
    - [ ] **Contextual Detail Drawer**: Add a UI toggle to shift Ticker Details from a centered Modal into a **Right-Side Slide-out Drawer**, allowing users to maintain context over the main data grid while scanning details.
    - [ ] **Sticky Table Columns**: Ensure the Ticker symbol and essential action buttons remain pinned as sticky columns when scrolling horizontally across very wide data tables.
    - [ ] **Ag-Grid Column Chooser**: Provide a user-facing column chooser dropdown to allow operators to hide/show specific columns dynamically, allowing them to manage excessive horizontal scrolling.

### Scheduler Management (UI)
- [ ] **Control Panel**:
    - [ ] Pause / Stop Scheduler.
    - [ ] Resume Scheduler.
    - [ ] View Scheduler Logs (live stream?).
    - [ ] View Scheduler Status/Health.
    - [ ] View/Edit Scheduler Config/History.
    - [ ] **API**: Create endpoints for Job Control (Pause/Resume/Trigger).
    - [ ] **UI**: Websocket/SSE connection for real-time log streaming.

### Debug Console / Terminal
- [ ] **Developer Console**:
    - [ ] Add a UI panel for developer or power-user diagnostics.
    - [ ] View raw data from selected API endpoints for faster debugging.
    - [ ] Display backend logs or log excerpts in near real time.
    - [ ] Provide guarded buttons to trigger specific backend jobs manually (for example Sync Trades).

### Help & Onboarding
- [ ] **Contextual Hints**: Hover tooltips explaining formulas/metrics.
    - [ ] Create generic `Tooltip` component in React.
    - [ ] Define "Glossary" JSON for central term management.
- [ ] **AI Chatbot Integration**: Side-panel chat to answer questions about dashboard data.
- [ ] **Data Helper**: Explains why an asset is juicy fruit, opportunity, or current focused financial item's status. 

---

## 5. Agentic AI & Intelligence
**Owner:** Antigravity Data | **Goal:** Force multiplication via AI agents.

### Capabilities
- [ ] **Prototype Agent**:
    - [ ] Lumibot is a fast library that will allow you to easily create trading robots for many different asset classes, including Stocks, Options, Futures, FOREX, and more. (documentation) https://lumibot.lumiwealth.com/
    - [x] **Agent Framework Research**: See [Agent Frameworks](learning/agent-frameworks.md). Discusses LangChain vs Lumibot vs Hybrid approach.
    - [ ] Juicy Fruit Opportunity Finder for a given stock or option (diagonal spread or close position (stop loss or take advantage of momentum), or keep to expiration).
    - [ ] Define Agent Toolset (Price Lookup, Greeks Calculator, Database Query).
    - [ ] Setup Orchestration (LangChain/LangGraph). 
- [ ] **Local Model Hosting**:
    - [ ] Evaluate robust local LLMs (Llama 3, Mistral) vs Cloud APIs.
    - [ ] Hardware requirements vs Cost.
    - [ ] Benchmark Inference Speed on Local Hardware.
- [ ] **Framework Prototype**:
    - [ ] Create simple "Stock Market Chatbot" using LangChain + OpenAI.
    - [ ] Test RAG capabilities on `docs/`.
    - [ ] Create Streamlit or Gradio quick prototype for validation.
- [ ] **Tooling Research**:
    - [ ] Scikit-learn: Best practices for this specific project?
    - [ ] MLflow: Is it overkill or necessary for experiment tracking?

---

## 6. Risk Management & Safety 
**Owner:** Risk Officer | **Goal:** Protect capital.

- [ ] **Guardrails**:
    - [ ] **Position Limits**: Max allocation per ticker/sector.
        - [ ] **Limits**: Both "Soft Warnings" (UI alert) and "Hard Blocks" (prevent order), initially platform will not have access to trade execution, so only soft warnings.
        - [ ] Recommend value limits and add a setting to define default limits (e.g., 5% max allocation).
    - [ ] **Slippage Control**: Warnings for illiquid options.
    - [ ] **Stop Rules**: Auto-exit criteria.
    - [ ] **"Ken's Bad Trades"**: Specific heuristic to detect and block historically poor impulsive setups.
    - [x] **Bad Trade Heuristics**: See [Bad Trade Heuristics](learning/bad-trade-heuristics.md). Lists specific patterns to block (0DTE, Impatience, etc.).

---

## 7. Agile & Project Governance
**Rules for Agents working on this **
1.  **Decomposition**: Evaluate features and requirements, elaborate them, make sure if required add a new feature/requirement to generate a learning-opportunity or implementation-plan document. That fits into the context window of the technical limitations of the LLM and the project. Add questions or highlight to the user for feedback as needed. 
2.  **Naming**: Use hierarchical IDs (e.g., `{feature_header}-{specific_feature_name}`) Don't use terms like epic or numbers which reflect sequences of water fall methodology, instead more agile scrum and names should be zen like reference to the function, page, or result. 
3.  **Parallelism**: Note if tasks can be run by multiple agents concurrently.
4.  **Next Steps**: If a feature is not completed, part of the plan should be next features-requirements to be implemented. 
4.  **Cleanup**: If reviewing, add a "Review and Cleanup" section.
5.  **Compliance**: Follow `.agent/rules/document.md` and `.agent/rules/implementation-plan.md`.

---

# Changelog

| Date | Action | Reason |
| :--- | :--- | :--- |
| 2026-02-01  | **REFINED** | Refined the document to be more specific and actionable. |
| 2026-02-01 | **REFACTORED** | Initial full cleanup and organization into Epics by AI Agent. |
| 2026-02-01 | **REFINED** | Split "Portfolio Management" into Analytics (Done) and History Visualization (Todo). |
| 2026-02-01 | **ADDED** | Added "Smart Roll / Diagonal Assistant" feature and marked "Opportunity Signals" as done. |
| 2026-02-17 | **FIXED** | Fixed Dividend Scanner bug (method typo + expanded lookahead 0-30 days + UTC fix). |
| 2026-03-21 | **ADDED** | Implemented per-account trade metrics widget in Trade History UI. |
| 2026-03-21 | **REFACTORED**| Updated P&L logic to support account-aware FIFO matching. |
| 2026-03-25 | **UPDATED** | Trade History UI: Collapsed Trade Count widget to save vertical space. |
| 2026-03-28 | **UPDATED** | Memorialized Stock Analysis ticker click popup (L120-L127): elaborated 8 sparse items into 20 detailed sub-items with `[x]` status for existing work. Created `stock_analysis_ticker_click.md` feature overview. |
| 2026-03-28 | **ADDED** | Created `CLAUDE.md` — Claude Code workspace config with project overview, code standards, UI/UX rules, and full file tree. Updated `ARCHITECTURE.md` with current file system tree and MongoDB collections table. |
| 2026-03-31 | **REVIEWED** | Compared `docs/features/roadmap-proposal-20260331.md` against the master F-R, skipped redundant items already captured in the source-of-truth, and merged new settings/debug-console requirements into `docs/features-requirements.md`. |
| 2026-04-02 | **ADDED** | Added pending-order-aware portfolio coverage requirements, including TWS working-order ingestion, optional Flex order-history backfill, and current-vs-if-filled coverage state rules. |
| 2026-04-02 | **UPDATED** | Implemented the first backend slice for pending-order-aware coverage: TWS open-order capture, Mongo `ibkr_orders` persistence, additive portfolio pending-effect fields, and regression tests. |
| 2026-04-02 | **UPDATED** | Implemented Portfolio/Trades UX slice: `Show "STK ?"` toggle behavior, pending-effect focus controls/badges, portfolio CSV export alignment with visible filtered rows, and Trade History ticker quick links with wider ticker column fit. |
| 2026-04-02 | **UPDATED** | Added a compact far-right Portfolio `Pending BTC` column (`P.BTC`) to improve visibility while reducing header width usage. |
| 2026-04-02 | **FIXED** | TWS position persistence now uses a contract-level key so multiple option legs (for example diagonals on the same underlying/account) are stored independently instead of overwriting each other. |
| 2026-04-02 | **FIXED** | Portfolio coverage labeling now leaves flat rows (`quantity == 0`) with blank `coverage_status` so zero-qty options do not appear as `Covered` in focus filters. |
| 2026-04-02 | **REVIEWED** | Full F-R review: added 3 new bug items to Section 0, promoted NAV date/account-scope items to `[/]`, promoted portfolio live-grid regression block to `[/]`, added decomposition guards to IB Gateway container and RAG System. See `docs/plans/F-R-review-2026-04-02.md`. |
| 2026-04-03 | **UPDATED** | F-R cleanup pass: closed implemented Portfolio quick-link and ticker-width items, promoted Near Money and Export items to done where code/tests already existed, and split `Last Price` into completed sort vs open price-filter sub-requirement (`portfolio-last-price-002`). |
| 2026-04-04 | **UPDATED** | Added DB-first data freshness architecture requirements (tiered freshness policy, source precedence, async refresh queue expectations, retention/indexing, and regression test requirements). |
| 2026-04-04 | **UPDATED** | Implemented first DB-first freshness coding sessions in API routes (`ticker`, `opportunity`, `signals`) including freshness metadata contract and stale-refresh queue behavior with regression tests. |
| 2026-04-04 | **UPDATED** | Extended DB-first freshness behavior to optimizer endpoint with backward-compatible `include_meta` support and added regression coverage for stale refresh queueing. |
| 2026-04-04 | **ADDED** | Added phased implementation plan for DB-first freshness rollout: `docs/plans/implementation_plan-20260404-data-freshness-db-first.md`. |
| 2026-04-04 | **UPDATED** | Signals endpoint now persists computed signal payloads back to `stock_data.signals` so subsequent requests can use DB-first cached signal data. |
| 2026-04-04 | **UPDATED** | Extracted stale-refresh dedupe/cooldown into reusable service `app/services/data_refresh_queue.py` and added dedicated regression tests for queue behavior. |
| 2026-04-04 | **UPDATED** | Stock analysis persistence now also writes append-style instrument price snapshots into `instrument_price_history` for charting/audit while preserving canonical latest snapshot in `stock_data`. |
| 2026-04-04 | **UPDATED** | Added DB-first ticker price-history API endpoint backed by `instrument_price_history` with freshness metadata and regression tests. |
| 2026-04-04 | **UPDATED** | Added automatic index creation for `instrument_price_history` (`instrument_key,timestamp` and `source,timestamp`) during stock-analysis persistence path with regression coverage. |
| 2026-04-04 | **UPDATED** | Added stock-ingest telemetry persistence for stock-live-comparison runs (`success`, `skipped`, `error`) into `stock_ingest_runs` with service-level regression tests. |
| 2026-04-04 | **UPDATED** | Freshness thresholds now support `system_config` override document (`_id: data_freshness_config`) while preserving safe defaults and test coverage. |
| 2026-04-04 | **UPDATED** | Added secured API settings endpoints for reading/updating data freshness thresholds (`/api/settings/data-freshness`) to operationalize DB-first freshness policy tuning. |
| 2026-04-04 | **FIXED** | Hardened ticker detail endpoint against JSON-serialization failures from non-finite numeric values (for example `NaN`) by sanitizing payload output and adding regression coverage. |
| 2026-04-04 | **FIXED** | Ticker modal loading now unblocks as soon as ticker detail data returns; slow secondary endpoints (for example optimizer) no longer hold the global spinner for the full timeout window. |
| 2026-04-04 | **UPDATED** | Ticker modal now lazy-loads secondary tabs on demand (signals/opportunity/optimizer/smart-rolls) and surfaces stale/fresh DB snapshot state in-panel instead of blocking first paint on parallel XHR fan-out. |
| 2026-04-04 | **UPDATED** | Added optional freshness metadata contract to `GET /api/analysis/rolls/{ticker}` via `include_meta=true` (backward-compatible list default) with regression tests for stale queue behavior. |
| 2026-04-04 | **UPDATED** | Added scheduler retention cleanup for `instrument_price_history` (default 730-day horizon with `system_config` override key `price_history_retention_days`) plus scheduler regression coverage. |
| 2026-04-04 | **UPDATED** | `GET /api/news/{symbol}` now follows DB-first behavior using cached `stock_data.profile.news` when available, supports optional freshness metadata (`include_meta=true`), and queues stale refresh asynchronously. |
| 2026-04-04 | **FIXED** | News route fallback now uses the implemented `NewsService` (`fetch_news_for_ticker`) instead of a missing `NewsSentimentService` import path. |
| 2026-04-07 | **UPDATED** | F-R cleanup pass: promoted stale partials to done where implementation/tests already existed (Ticker Click Popup, Portfolio Analytics, trade-history dividends, Expiring filter, Type-column regression, STK-only events bugfix, implementation-plan marker, and run-observability parent). Remaining work items stay open under their specific sub-requirements. |
| 2026-04-07 | **UPDATED** | Stock analysis yfinance HTTP knobs now read from `system_config` (`_id: stock_analysis_http_config`) so operators can tune `download_batch_size`, `batch_pause_sec`, and request throttle interval without code changes; added admin API endpoints (`/api/settings/stock-analysis-http`) and regression tests for override/coercion. |
| 2026-04-07 | **UPDATED** | Daily stock-analysis scheduler now supports sharded execution to reduce yfinance burst traffic. Added `scheduler_sharding_enabled`, `scheduler_shard_size`, and `scheduler_shard_pause_sec` settings in `stock_analysis_http_config`, wired `stock_comparison_job` to the sharded wrapper, and added scheduler tests for shard behavior. |
| 2026-04-07 | **UPDATED** | Dashboard admin settings UI now includes stock-analysis HTTP and scheduler sharding controls, and added runbook `docs/features/stock_analysis_http_scheduler_sharding.md` for UI/API/manual configuration and verification steps. |
| 2026-04-07 | **UPDATED** | Data-freshness review pass: added NYSE-aware session logic (holiday + early-close handling) for staleness evaluation, enforced source precedence fallback to `flex_eod` when TWS snapshots are stale, added backend regressions for source fallback/session windows, and extracted/tested frontend ticker-modal freshness banner formatting helper. |
| 2026-04-07 | **UPDATED** | Completed scheduler ingest telemetry diagnostics: `stock_ingest_runs` now persists `source_used`, `rows_updated`, `stale_hit_ratio`, `failure_count`, and `failures`; sharded scheduler summary now aggregates row/failure totals with regression coverage. |
| 2026-04-07 | **UPDATED** | Completed operator freshness-interval settings surface: added admin Dashboard Settings controls wired to `/api/settings/data-freshness`, enforced positive-int validation for freshness TTL config, and added frontend/backend regression coverage. |
| 2026-04-07 | **UPDATED** | Completed source-precedence integration coverage for freshness: added regression tests for TWS recent vs stale vs no-live-snapshot paths (`tws_live`/`flex_eod`) and confirmed yfinance fallback coverage for DB-missing routes. |
| 2026-04-07 | **UPDATED** | Completed canonical instrument identity normalization: added shared secType-aware keying service, switched stock price-history persistence to canonical `instrument_key` values with legacy-read compatibility, and added regression tests for key formatting and route query behavior. |
| 2026-04-07 | **UPDATED** | Added lightweight `instrument_snapshot` persistence and read fallback: stock ingest now writes canonical latest-per-instrument snapshots, and ticker freshness paths can use snapshot metadata when `stock_data` is missing. |
| 2026-04-07 | **UPDATED** | Finalized freshness policy definitions: added explicit tier/SLA policy doc and endpoint-tier mapping, promoted policy items to done, and added regression tests proving Tier A/B/C endpoint thresholds evaluate differently under the same timestamp. |
| 2026-04-07 | **UPDATED** | Completed ticker-detail items `Stock Analysis-Opportunities` and `Stock Analysis-Optimizer` (`stock-analysis-optimizer-juicy-table-001..008`): added DB-first persisted `juicy_opportunities` model, Juicys top-nav workspace, optimizer tab table/presets/top-N selector, and async refresh-job queue path. |
| 2026-04-07 | **UPDATED** | Added new requirements for `Juicys` top navigation workspace and ticker-modal Optimizer `Juicy Fruits` table contract (sortable/filterable columns, top-N selector, DB-first refresh-job behavior, and persistence/grading alignment). |
| 2026-04-07 | **UPDATED** | Implemented `stock-analysis-optimizer-juicy-table-009..011`: chain-level generation now evaluates 4 expiries x (1 ITM + 4 OTM) call-sale candidates per ticker, adds liquidity/timeframe qualifiers (`volume`, `open_interest`, `spread_pct_mid`, `liquidity_grade`, `timeframe_bucket`), and applies short-DTE ranking with spread/liquidity penalties; covered by `tests/test_juicy_service.py`. |
| 2026-04-08 | **UPDATED** | Closed remaining Stock Analysis modal UX polish items for analytics layout, `COPY INFO` formatting, and `found=false` telemetry badge/logging; also expanded Portfolio viewport usage to reduce workspace compression on `?view=PORTFOLIO`. |
