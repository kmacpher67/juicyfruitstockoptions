# Features & Requirements Planning & Roadmap
- When reading this document to perform work:
    - Follow all the rules documented in the workspace rules & workflow .md docs
    - The .gemini global rules rules file should be followed. 
    - When doing work from this document follow the `.agent/workflows/create-a-plan.md` workflow!

> [!NOTE]
> This document serves as the "Wish List" and high-level roadmap for the Juicy Fruit Stock Options project. It is **not** a strict project plan but a collection of Todo items (maybe large feature sets with requirements) to guide future development. Items are not in any particular order. This Epic document should be used like Kanban board per Status Legend to mark items. 

**Status Legend:**
- [ ] Proposed / Todo
- [/] In Progress
- [x] Done (Move to Changelog)
- [!] Blocked / Needs Research

---
# Implementation 
- When performing an implementation plan based on items in this epic document, i would use the following rules:
-- All the rules documented in the workspace rules & workflow .md docs should be followed
-- The .gemini global rules rules file should be followed. 
-- An implementation plan should be broken down into smaller items (added to the Epic Todo list as sub items) that can be completed in a reasonable amount of time (e.g., 1-2 hours)
-- The incremental implementation plan should follow hierarchical decomposition for naming based the short name of the epic (e.g., epic-001-algorithmic-trading-001-task-001)

## 0. Bugs, Fixes, & Maintenance
- [ ] 

## 1. Project Mission & Context
The goal of this project is to build a robust, semi-automated trading dashboard ("Juicy Fruit") that aids **Trader Ken** in analyzing options, managing risk, and executing strategies (e.g., covered calls, wheel strategy). It combines data from IBKR, algorithmic analysis, and modern web technologies.

*   **Reference Docs**:
    *   `.agent/rules/trader-ken.md` (Trading Logic)
    *   `README.md` (Technical Setup)

---

## 2. Infrastructure & Modernization (Epic 1)
**Owner:** TBD | **Goal:** reliable, secure, and strictly typed foundation.

### Documentation & Knowledge Management
- [ ] **Mcp server md-converter**: Create tool to convert .md files to .docx for memorization/sharing.
    - [ ] Research `python-docx` vs `pypandoc` for compatibility.
    - [ ] Create CLI entry point or API endpoint for conversion.
- [ ] **Google Docs Migration**: define rules/plans to store non-code docs (blobs, excel) in Google Docs vs Info storage.
    - [ ] **[?] QUESTION**: Do we have a specific Google Service Account or OAuth Client setup, or need one created?
    - [ ] Implement Google Drive API client wrapper.
    - [ ] Define folder structure mapping (Local <-> Drive).
- [ ] **RAG System (Documentation)**: Implement RAG (Retrieval-Augmented Generation) for asking questions about the codebase/docs.
    - [ ] Select Vector Database (e.g., ChromaDB, Pinecone, FAISS).
    - [ ] Develop Document Ingestion Pipeline (Markdown -> Embeddings).
    - [ ] Create Chat Interface for querying docs.

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
    - [ ] Auto-logout UI if backend token expires.
    - [ ] Synced session state between generic React usage and Python backend.
    - [ ] Implement "Remember Me" vs "High Security" modes.
- [ ] **Settings Management**:
    - [ ] Admin defaults vs User overrides.
    - [ ] Enforce "minimum safe settings" that users cannot override.
    - [ ] Define Configuration Schema (using Pydantic).
    - [ ] Create Frontend UI for editing allowed settings.

### Data Reliability
- [ ] **Mongo Backup Automation**:
    - [ ] Automate backup to GitHub (current manual process).
    - [ ] Investigate Google Drive as alternative storage.
    - [ ] *Action*: Have agent follow `learning-opportunity.md` to recommend best backup practices.
- [ ] **TWS API container**: Evaluate need for a dedicated TWS API Docker container for stable IBKR connection, and create more epic items as neccessary.
    - [ ] Research standard IBC-based containers (e.g., `mvberg/ib-gateway-docker`).
    - [ ] Test reliability of headless TWS vs IB Gateway. 

### Observability & Logging
- [/] **Logging**: Implement logging for all backend services.  
    - [/] Implement detailed DEBUG - **Style:** preface all logs with "{datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}"    the message text should tell the user what is happening (if possible, include the result of the action)
- [ ] **Logging**: Implement logging for all frontend services. 
    - [ ] Research centralized logging (e.g., sending frontend logs to backend API).
    - [ ] Implement React Error Boundary logging. 
- [ ] **Structured Logging:** Use the standard `logging` library.
- [ ] **Levels:** `DEBUG` (internal state), `INFO` (milestones), `ERROR` (exceptions with `exc_info=True`).
- [ ] **Traceability:** Errors must provide context (e.g., "Failed to process file X due to Y").

---

## 3. Algorithmic Trading Engines (Epic 2)
**Owner:** Ken | **Goal:** Automated insights and strategy backtesting.

### Portfolio Management
- [/] **Portfolio Analytics**: Show Key Performance Indicators (NAV, d/w/m/y changes) on the Portfolio Dashboard (via `NAVStats`).
- [ ] **Portfolio History Visualization**: Implement interactive time-series chart for NAV performance.
    - [ ] **Frontend**: Add graph component (e.g., Recharts) to "My Portfolio" view using data from `/portfolio/stats` (history field).
    - [ ] **Business Logic**: Implement Cost Basis and Realized P&L calculation (grouping buys/sells by symbol).
    - [ ] **Ticker Analytics**: Sneak peek at the ticker analytics endpoint (ie: `/ticker/{symbol}`) to show the most recent stats for an individual ticker. 
    - [ ] **Opportunity Finder**: Implement Opportunity Finder (ie: `/opportunity/{symbol}`) to show the most recent stats for an individual ticker. 
    - [ ] **Portfolio Optimization**: Implement Portfolio Optimization (ie: `/portfolio/optimizer/{symbol}`) to show the most recent stats for an individual ticker. 

- [x] **Trade History Management**: Get entire history of trades (ie: with cost basis) and all relevant metrics
    - [x] Ingest Legacy Trade Files (See [Legacy Trade Ingestion](features/legacy_trade_ingestion.md))
    - [x] **Backend API**: Create `/api/trades` endpoint to serve historical data with pagination/filtering.
    - [x] **Business Logic**: Implement Cost Basis and Realized P&L calculation (grouping buys/sells by symbol).
    - [x] **Frontend**: Build "Trade History" view with datagrid, filtering, and export.
    - [x] **Metrics**: Add summary metrics (Total P&L, Win Rate, LT/ST P&L, etc.) to the history view.
    - [x] **Bug issue**: History view is not loading trades, 500 Internal Server Error http://localhost:3000/api/trades/analysis
    - [x] **Bug issue**: Portfolio view sub menu is dropping down when going to the trades menu tab. 
    - [ ] **learning opportunity**: Explain Win Rate, Profit Factor, and other metrics in the trade history view. How are they calculated? What impact does a diagonal roll have on the metrics aka: loss but it gives a underlying STK additional unrealized profit? How are dividends factored into the metrics?
    - [ ] **time window**: For trade history view, can we implement a time window starting with MTD, having 1D, 1W, 1M, 3M, 6M, 1Y, 5Y,and All trades?

### Analysis & Signals
- [ ] **"Juicy" Opportunity Finder**:
    - [ ] Screen for covered call candidates (high premiums, stable/upward trend).
    - [ ] Screen for call buying opportunities (momentum).
    - [ ] Strategy: Use "Juicy Calls" premium to fund downward protection (puts) or long calls.
    - [ ] **Learning Opportunity**: What are the specific quantitative thresholds for "Juicy"? (e.g., IV Rank > 50, Delta 0.3-0.4?). Use .agent/workflows/learing-opportunity.md to guide this process.
    - [ ] Implement Scanners/Screeners module in Python.
- [ ] **Targeting Logic**: Integrate Macro trends and News events into the analysis and portfolio views.
    - [ ] Integrate external News API (e.g., NewsAPI.org or IBKR News feed).
    - [ ] Fetch Macro indicators (Fred API? Inflation, Interest Rates).
    - [ ] Create "Impact Score" for news events on portfolio tickers.
- [ ] **Kalman Filters**: Implement Kalman filters for signal generation.
    - [ ] Research `filterpy` or `pykalman` libraries.
    - [ ] Prototype Mean Reversion and Trend Following models using Kalman.
    - [ ] **Learning Opportunity**: .agent/workflows/learing-opportunity.md Is there a specific paper or reference strategy triggering the interest in Kalman Filters in trading, and portfolio management?

### Strategy & Backtesting
- [ ] **Backtesting Engine**:
    - [ ] Ability to "back play" strategies using historical IBKR data.
    - [ ] Evaluate libraries: Zipline, VectorBT, or custom.
    - [ ] **Engine Selection**: Do you prefer an event-driven engine (slower, more realistic) or vectorized (faster, less realistic)? use this workflow .agent/workflows/learing-opportunity.md to explain this to me and what matters in this decision. 
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

## 4. Dashboard & UX Features (Epic 3)
**Owner:** Frontend Team | **Goal:** A "Wow" factor UI with actionable data.

### Visualizations
- [ ] **Interactive Graphs**:
    - [ ] Stock Price vs Moving Averages (interactive, zoomable).
    - [ ] Local graphs for private portfolio performance.
    - [ ] Evaluate Charting Libraries (Recharts, Chart.js, Plotly).
    - [ ] **Performance**: Do you prefer performance (Canvas - good for high frequency) or interactivity (SVG - good for tooltips/css)? generally svg is better for interactivity for a small user base, but even for just me not too slow.
- [ ] **Yield Analysis**: Visuals for Yield vs Cost Basis vs ROI.
    - [ ] Implement Heatmap visualization for Option Greeks.

### Scheduler Management (UI)
- [ ] **Control Panel**:
    - [ ] Pause / Stop Scheduler.
    - [ ] Resume Scheduler.
    - [ ] View Scheduler Logs (live stream?).
    - [ ] View Scheduler Status/Health.
    - [ ] View/Edit Scheduler Config/History.
    - [ ] **API**: Create endpoints for Job Control (Pause/Resume/Trigger).
    - [ ] **UI**: Websocket/SSE connection for real-time log streaming.

### Help & Onboarding
- [ ] **Contextual Hints**: Hover tooltips explaining formulas/metrics.
    - [ ] Create generic `Tooltip` component in React.
    - [ ] Define "Glossary" JSON for central term management.
- [ ] **AI Chatbot Integration**: Side-panel chat to answer questions about dashboard data.
- [ ] **Data Helper**: Explains why an asset is juicy fruit, opportunity, or current focused financial item's status. 

---

## 5. Agentic AI & Intelligence (Epic 4)
**Owner:** Antigravity Data | **Goal:** Force multiplication via AI agents.

### Capabilities
- [ ] **Prototype Agent**:
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

## 6. Risk Management & Safety (Epic 5)
**Owner:** Risk Officer | **Goal:** Protect capital.

- [ ] **Guardrails**:
    - [ ] **Position Limits**: Max allocation per ticker/sector.
        - [ ] **Limits**: Both "Soft Warnings" (UI alert) and "Hard Blocks" (prevent order), initially platform will not have access to trade execution, so only soft warnings.
        - [ ] Recommend value limits and add a setting to define default limits (e.g., 5% max allocation).
    - [ ] **Slippage Control**: Warnings for illiquid options.
    - [ ] **Stop Rules**: Auto-exit criteria.
    - [ ] **"Ken's Bad Trades"**: Specific heuristic to detect and block historically poor impulsive setups.
    - [ ] **Bad Trade Heuristics**: Please list specific "Bad Trade" patterns to detect (e.g., 0DTE, low liquidity, earnings plays). Create a.agent/workflows/learing-opportunity.md document to learn and discuss more about bad trades and heuristics.

---

## 7. Agile & Project Governance
**Rules for Agents working on this Epic:**
1.  **Decomposition**: Break Epics into tasks of ~1-2 hours.
2.  **Naming**: Use hierarchical IDs (e.g., `epic-001-trading-001-task-001`).
3.  **Parallelism**: Note if tasks can be run by multiple agents concurrently.
4.  **Cleanup**: If reviewing, add a "Review and Cleanup" section.
5.  **Compliance**: Follow `.agent/rules/document.md` and `.agent/rules/implementation-plan.md`.

---

# Changelog

| Date | Action | Reason |
| :--- | :--- | :--- |
| 2026-02-01  | **REFINED** | Refined the document to be more specific and actionable. |
| 2026-02-01 | **REFACTORED** | Initial full cleanup and organization into Epics by AI Agent. |
| 2026-02-01 | **REFINED** | Split "Portfolio Management" into Analytics (Done) and History Visualization (Todo). |