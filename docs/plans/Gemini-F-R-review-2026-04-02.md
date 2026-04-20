# F-R Review - Gemini AI - 2026-04-02

> Follow-up (2026-04-19): Juicys Follow-up/Review queue planning has been split into dedicated docs:
> [Juicy Follow-up/Review (F-R) Workflow](../features/juicy_fr_followup_review.md) and [Implementation Plan](implementation_plan-20260419-juicy-fr-followup-review.md).

## 1. Item Counts
Based on an analysis of `docs/features-requirements.md`:
- **Open `[ ]` items**: 45
- **In Progress `[/]` items**: 21
- **Closed `[x]` items**: 120

*(Note: Sub-items count independently toward the totals. The F-R document is actively maintained and dense, reflecting significant recent progress in realtime integration, filtering, and data reliability).*

## 2. Open Items Lacking Code/Test Ecosystem
Many open items in the F-R are "Wish List" or highly aspirational, meaning they are not yet mentioned in the frontend, backend, or test suites, nor do they have dedicated `docs/features/` tracking documentation. 

**Review of conceptual items missing code footprint:**
- **Infrastructure & Docs:** "Mcp server md-converter", "Google Docs Migration", "RAG System (Documentation)", "Local vs Cloud Analysis", "Docker Hardening". These are pure dev-ops/infrastructure tasks with zero codebase or test impact yet.
- **Agentic AI & Intelligence:** "Local Model Hosting", "Stock Market Chatbot", "Tooling Research (Scikit-learn, MLflow)". 
- **ML in the Loop (8-Step Flow):** "Universe Selection", "Feature Engineering", "Time-Series CV", "Model Training", "Validation", "Signal Creation". This entire section is highly theoretical and lacks back-end hooks or tests.
- **Backtesting & Algorithms:** "Backtesting Engine (Zipline, VectorBT)", "Metric Stack (empyrical)", "Personal Trading History (RAG for Trading History)".
- **UI Epics Without Skeleton Code:** "Developer Console", "Control Panel (Scheduler Control)", "Interactive Graphs (Recharts/Chart.js Canvas vs SVG)".

*Recommendation:* These items should be labeled with `[!] Needs Research` or moved to a dedicated `Wish List` epic to declutter the actionable F-R view until Ken is ready to initiate a dedicated planning stage for them.

## 3. Code Review: Potentially Completed Open Items
A code review of recent changes against the open items list reveals several tasks that appear to be completed (or significantly mitigated) by recent work:

1. **`[ ] 1D NAV UI: The 1 day NAV is showing 0, there something broken with the logic.`**
   - **Why it looks done:** The `ibkr-tws-jobs-002` item was marked complete, noting: *"Add `run_tws_nav_snapshot()` job... Fixes the 1D NAV showing 0 bug — intraday data points will now exist."*
   - **Action:** Can likely be marked `[x]`.

2. **`[ ] Last Price: Sort and filter by last price.` (Portfolio List)**
   - **Why it looks done:** The PortfolioGrid uses generic DataGrid components which inherently support clicking the `Last Price` column header to sort. If explicit filtering by a price threshold is needed, it remains open, but the sorting functionality is natively present.
   - **Action:** Verify sorting works natively and close; specify if a dedicated numerical filter UI is required.

3. **`[ ] Target Logic: Research: Evaluate X (Twitter) API v2` & `Investigate Yahoo Scout integration`**
   - **Why it looks done/obsolete:** The `News Feeds` backend has already been implemented with a capable news aggregator. Depending on whether Twitter is still a strict requirement, the core intent of "macro news targeting" might be functionally complete.
   - **Action:** Evaluate if Twitter/Yahoo scrape is still needed or if current NewsAPI integration satisfies the use case.

4. **`[ ] xdiv signal: widget should scan ALL/any stocks upcoming dividend x-div date in the analysis ticker list and not just the current portfolio stocks.`**
   - **Why it looks done:** Recent fixes to the corporate events and x-div scanner expanded the lookahead window (30 days) and isolated logic to underlying `STK`s. If it scans the core ticker list table rather than just portfolio, this is likely satisfied.
   - **Action:** Run a test against a non-portfolio analysis ticker to confirm the xdiv scanner picks it up, then mark `[x]`.

5. **`[ ] Stock Analysis-Analytics: expanded to surface all ~40 analysis columns`**
   - **Why it looks partially done:** The backend `stock_live_comparison.py` now parses all variables successfully, and the main Stock Analysis Grid was updated to handle many more columns. The *Analytics tab* in the TickerModal specifically might still be restricted, but the underlying data pipe is 100% complete.
   - **Action:** Requires minor UI work in `TickerModal.jsx` to map the remaining properties to table rows.

6. **`[ ] Stock Analysis-Opportunities: Surface actionable Buy/Sell recommendations in Opportunity tab...`**
   - **Why it looks partially done:** Opportunities (`GET /api/opportunity/{symbol}`) are now exposed to the Ticker Modal. Dividend capture and Expiration scanners are actively contributing metrics. 
   - **Action:** Re-evaluate exactly what "Buy/Sell" flag is missing from the existing opportunity score rendering.

## Next Steps
- Verify the potentially completed items.
- Merge the status of confirmed completed items into `docs/features-requirements.md`.
- Consider breaking down the "theoretical" F-R components (e.g., ML Flow) into separate roadmap documents if they clutter the immediate development pipeline.

## 4. Code Review of `[/]` In-Progress Items

After manually reviewing the `[/]` items in the F-R document and cross-referencing recent commits (especially the realtime portfolio grid, stats/coverage, and dividend implementations), here is an actionable assessment for each. Many items act as "Epics" where all or most sub-tasks are already `[x]`, and they simply need to be closed or decomposed.

### A. Ready to Mark `[x]` (Completed by Recent Work)
These epics or tasks have been thoroughly handled by recent implementations.

1. **`Portfolio Analytics: Show Key Performance Indicators... on Portfolio Dashboard` (L295)**
   - **Review:** The entire `NAVStats` module has been overhauled, supports multiple timeframes, account scoping, and real-time/TWS metrics.
   - **Action:** Mark `[x]`.
2. **`Options Due in X Days`, `OTM / Near Money filter`, `Underlying STK inclusion for option filters` (L342-L344)**
   - **Review:** Portfolio grid toolbar now robustly handles `Expiring (<N)`, `Near Money (<N%)`, and combined stock filters in `PortfolioFilters.jsx`.
   - **Action:** Mark `[x]`. 
3. **`Covered/Uncovered/Naked Filter` (L357) & `Uncovered Filter` (L353)**
   - **Review:** Comprehensive filtering and backend coverage status was implemented and locked with tests in `tests/test_coverage_status.py`. 
   - **Action:** Mark `[x]`.
4. **`Portfolio Coverage Status Regression` (L358)**
   - **Review:** All 5 sub-items (001 through 005) are already marked `[x]` and unit tests exist. 
   - **Action:** Mark the parent epic `[x]`.
5. **`Export: Export current view of portfolio to CSV` (L375)**
   - **Review:** All 4 export alignment rules (001-004) are already marked `[x]` and tested.
   - **Action:** Mark the parent epic `[x]`.
6. **`Frontend: Create a new modal window that pops up an overlay with the ticker analytics...` (L304)**
   - **Review:** This is a duplicate description of the "Ticker Click Popup" (L275) which was successfully memorialized into `TickerModal.jsx`. 
   - **Action:** Mark `[x]` (or delete as a redundant duplicate).

### B. Remaining Active `[/]` Trackers (Keep `[/]`)
These items correctly reflect active, ongoing work where significant sub-tasks remain open.

1. **`portfolio-live-grid-undefined-values` (L42) & `Portfolio View — TWS Live Grid Regression Fixes` (L382)**
   - **Review:** Fixes `001` and `002` landed, but `003` through `006` remain open (e.g., `Type` detection and merged source shapes).
   - **Action:** Keep `[/]` until the final regressions are resolved.
2. **`IBKR Pending Orders — Real-Time + Flex-Aware` (L189) & `Pending Order Aware Coverage / Roll State` (L364)**
   - **Review:** Heavy recent progress, but `ibkr-orders-003, 005, 012, 013` and the UI visual states for orders remain open. 
   - **Action:** Keep `[/]`.
3. **`Stock Analysis — Ticker Click Popup` (L275)**
   - **Review:** 8 of 9 tasks are done. Only "All ~40 Columns in Analytics Tab" remains.
   - **Action:** Consider extracting "All ~40 Columns" into a standalone `[ ]` task and marking the Ticker Modal epic as `[x]`.
4. **`trade history / dividends` (L321)**
   - **Review:** Backend parser and Flex report setup is done (`[x]`), but frontend Trades View / Portfolio UI integration remains open (`[ ]`).
   - **Action:** Keep `[/]` until the UI effectively renders the dividend metrics.

### C. Dormant Tasks: Return to `[ ]` and Decompose
These tasks are currently idle. They were marked `[/]` at some point but no active development is happening on them. By returning them to `[ ]`, we keep the "In Progress" view focused.

1. **`UI fixes` (L410-L413)**
   - **Review:** Points out bugs with `Type` column, trades view `STK/OPT`, XDTE boxes width, and XDTE 2D/4D display. 
   - **Action:** Decompose into 4 specific standalone `[ ]` bugs and mark them open. No need to keep them grouped as `[/]`.
2. **`Dividend Feed` / `events` tracking (L438, L447-L450)**
   - **Review:** The scanner fetches data, but the explicit UI features (Yahoo Finance link, fixing empty fields like Target, UI analysis panel) are pending. 
   - **Action:** Roll these into a new `[ ] Dividend & Corporate Events UI` epic.
3. **`Markov Chains` / `NEXT STEP:` integrations (L483-L492)**
   - **Review:** Backend Kalmon filters are functioning, but the UI hooks and Smart Roll algorithmic logic remain untouched. 
   - **Action:** Revert parent to `[ ]`. Ensure the "NEXT STEP" items are properly tracked as open sub-tasks.
4. **`PRICE ACTION` (L500)**
   - **Review:** Highly aspirational. Concepts like BOS, FVG, and HH/LL have zero codebase footprint. 
   - **Action:** Revert context items to `[ ]`. This needs a heavy dedicated planning session to become actionable code.
5. **`Trading Agent` (L526)**
   - **Review:** Was likely spiked/researched, but no immediate LLM loop is actively governing trades. 
   - **Action:** Revert to `[ ]` and move to the Agentic AI epic bucket.
