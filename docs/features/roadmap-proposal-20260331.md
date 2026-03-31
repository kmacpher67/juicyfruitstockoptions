# Juicy Fruit - Features & Requirements Roadmap (Revised)

> [!NOTE]
> This document is a living "Wish List" and high-level roadmap, not a strict project plan. It guides future development and is used to track ideas and features. Items are organized by functional area.

**Status Legend:**
- [ ] **Todo**: Proposed or not yet started.
- [/] **In Progress**: Actively being worked on.
- [x] **Done**: Completed and validated.
- [!] **Blocked / Needs Research**: Requires investigation or dependencies are not met.

---

## 1. Project Vision & Core Principles

The goal is to build a robust, semi-automated trading dashboard ("Juicy Fruit") that aids **Trader Ken** in analyzing options, managing risk, and executing strategies. It combines data from IBKR, algorithmic analysis, and modern web technologies.

### UI/UX Design Standards
- **Tool to help me**: This is a tool to help me trade, track, and identify opportunities in the stock market across three accounts.
- **Density over Fluff**: Prioritize data tables and comparative metrics over large buttons/empty space.
- **Yield-First**: Every opportunity MUST display an "Annualized Yield %" and "Total Potential Return".
- **Portfolio Positions**: Opportunities and analysis should be filterable by account. Positions should be condensed with a float-over or detail drawer for more info.
- **Comparison View**: All tables should be sortable, searchable, and filterable by any column.
- **No Floating Modals for Core Data**: Use an expandable "Detail Drawer" on the right side of the screen to maintain the context of the main list.

---

## 2. Application Roadmap

### **Area: Frontend & User Experience (UX)**

#### Portfolio Dashboard (`?view=PORTFOLIO`)
- [/] **Portfolio Analytics (NAV)**: Show Key Performance Indicators (NAV, d/w/m/y changes) on the Portfolio Dashboard via `NAVStats`.
- [ ] **Portfolio History Visualization**: Implement an interactive time-series chart for NAV performance using data from `/portfolio/stats`.
- [x] **Remove Opportunities**: The main portfolio grid should display owned positions, not opportunities.
- [ ] **Advanced Filtering System**: Implement a robust filtering system for the portfolio list.
    - [X] **Account Filter**: Filter by account number.
    - [X] **Covered/Uncovered/Naked Filter**: Filter positions based on whether the stock quantity is fully covered by short options.
    - [ ] **Options Expiring Soon**: Filter for options expiring within a user-configurable number of days (DTE).
    - [ ] **Near the Money (OTM/ITM)**: Filter options that are within a certain percentage of the strike price.
- [x] **Export to CSV**: Export the current filtered view of the portfolio to a CSV file.
- [x] **Link to Ticker Analysis**: Add a link next to each ticker to open the shared `TickerModal` for in-depth analysis.
- [x] **UI Layout**: Increase the width of the portfolio view to prevent horizontal scrolling and optimize column widths.
- [ ] **Portfolio TWS Live Grid Regression Fixes**: As of 2026-03-31 the `?view=PORTFOLIO` grid shows multiple realtime rendering regressions after the TWS integration work. See `docs/features/portfolio_tws_live_grid_regressions_20260331.md`.
    - [ ] **portfolio-live-grid-001**: Price, Value, Basis, and Unrealized PnL must never render the literal text `undefined`; when live data is unavailable the UI should show a deliberate fallback value and keep numeric formatting stable.
    - [ ] **portfolio-live-grid-002**: Restore correct security type classification and display for `STK` vs `OPT`, including option-specific description details and any Type-driven links/actions.
    - [ ] **portfolio-live-grid-003**: `% NAV` must not render `NaN%`; row-level percent calculations must guard against missing denominators and unavailable live values.
    - [ ] **portfolio-live-grid-004**: Re-verify the pre-TWS Type-column fallback logic that was previously documented as fixed so the same regression is not reintroduced.


#### Trade History (`?view=TRADES`)
- [x] **Trade History Management**: Ingest, process, and display the entire history of trades with correct cost basis and metrics.
- [x] **Time Window Filter**: Implement a time window filter (1D, 1W, 1M, YTD, ALL, etc.). Default to YTD.
- [x] **Account-Aware Metrics**: Display metrics (Total P&L, Win Rate, etc.) broken down by account and for "All" accounts.
- [/] **RT Trades Availability & Diagnostics**: Treat RT Trades as a runtime-verified feature, not just a clickable UI mode.
    - [ ] Surface `handshake_failed` distinctly when the backend can reach the IBKR socket but the API handshake does not complete.
    - [ ] Add `?view=TRADES` unavailable-state messaging that explains RT Trades require the same-runtime IBKR handshake, not only raw TCP reachability.
    - [ ] Persist and expose current-day TWS executions only after `reqExecutions` / `execDetails` / commission handling are implemented end to end.
- [/] **Dividends in Trade History**: Incorporate cash dividends into the trade history view for accurate return calculations.
    - [x] **Flex Report**: A new Flex Query for cash transactions has been configured.
    - [ ] **Backend Parser**: Update `ibkr_service.py` to parse the new dividend report and store it.
    - [ ] **UI Integration**: Display dividends in the trade history view.
- [ ] **UI Enhancements**:
    - [x] Fix metric recalculation when changing timeframes.
    - [x] Add more data fields: AssetClass, Put/Call, NetCash, etc.
    - [x] Improve layout of metric widgets to fit account breakdowns.

#### Stock Analysis & Screening (`?view=ANALYSIS`)
- [x] **Stock Analysis Grid**: Display a sortable, filterable grid of tickers with key metrics (Call/Put Skew, Momentum, MAs, etc.).
- [x] **Live Analysis & Report**: Generate and download an `.xlsx` report with ~40 columns of analysis data.
- [x] **Ticker List Management**: Allow creating, updating, and deleting ticker lists.
- [ ] **Composite Rating**: Aggregate all metrics into a single, color-coded "Ticker Health" score.
- [ ] **Bug Fix**: The live analysis feature broke recently. It needs to be investigated and fixed.

#### Ticker Details Modal
- [/] **Ticker Click Popup**: A comprehensive, multi-tab modal window that opens when a ticker is clicked anywhere in the app.
    - [x] **6 Tabs Implemented**: Analytics, Signals, Opportunity, Optimizer, Price Action, Smart Rolls.
    - [x] **Backend APIs**: Dedicated endpoints for each tab's data needs.
    - [ ] **Analytics Tab Expansion**: Expand to show all ~40 columns from the analysis spreadsheet.
    - [x] **Profile Tab**: Add a new tab for company profile info (Description, Sector, Industry).
    - [/] **Header Enhancement**: Improve the modal header to include the company's full name and links to Google/Yahoo Finance.

#### Configuration & Settings UI
- [ ] **New Settings Page**: Create a dedicated UI for managing user preferences and application settings.
    - [ ] **UI Preferences**:
        - [ ] Default time view on the Trades page.
        - [ ] Grid density and column visibility.
        - [ ] Theme (Dark/Light).
    - [ ] **Backend & NFR Configuration**:
        - [ ] Manage feature flags (e.g., `IBKR_TWS_ENABLED`).
        - [ ] Securely manage API keys (e.g., Google API Key).
        - [ ] Configure scheduler intervals.
    - [ ] **Admin vs. User Settings**: Define defaults and user-overridable settings.

#### General UI/UX
- [ ] **Interactive Graphs**: Implement interactive, zoomable graphs for stock prices and portfolio performance.
- [ ] **Help & Onboarding**:
    - [ ] **Contextual Hints**: Add tooltips to explain complex metrics and formulas.
    - [ ] **AI Chatbot**: An in-app chatbot to answer questions about the data.
- [ ] **Debug Console / Terminal**:
    - [ ] Implement a UI panel for developers/power-users.
    - [ ] View raw data from API endpoints.
    - [ ] Display real-time backend logs.
    - [ ] Provide buttons to trigger specific backend jobs manually (e.g., "Sync Trades").

---

### **Area: Backend & Services**

- [/] **Logging**: Standardize and improve logging across all backend services.
- [ ] **Authentication**:
    - [x] Auto-logout on token expiration.
    - [ ] Implement "Remember Me" functionality.
- [ ] **Scheduler & Background Jobs (`APScheduler`)**:
    - [ ] **UI Control Panel**: Build a UI to pause, resume, and monitor scheduler jobs.
- [ ] **Corporate Events Calendar**:
    - [/] Find all corporate events (Earnings, Splits) for tracked tickers.
    - [ ] Add events to the downloadable `.ics` calendar file.
    - [ ] Create a subscribable iCal URL endpoint.
- [ ] **Documentation Generation**:
    - [ ] Create a tool to convert project markdown files (`.md`) to `.docx`.

---

### **Area: Data & Infrastructure**

#### IBKR Data Integration
- [/] **IBKR Real-Time Data (TWS API)**: A major initiative to get live data via a persistent TWS/Gateway connection.
    - [ ] **Gateway in Docker**: Run IB Gateway as a Docker Compose service.
    - [/] **Python Service**: A thread-safe Python singleton (`ibkr_tws_service.py`) to manage the TWS connection.
    - [/] **Scheduler Jobs**: Sync live positions, NAV, and trades into MongoDB.
    - [/] **API Endpoints**: Expose live status and data to the frontend.
    - [/] **Frontend Indicator**: A UI badge showing live connection status.
    - [/] **Connection Reliability & Diagnostics**: Improve logging, reconnect logic, and provide clear error states (e.g., "Handshake Failed"). This is critical for debugging Docker-to-host connectivity.
    - [ ] **Trusted Runtime Setup**: Document and verify the exact TWS trusted-client / localhost-only API settings required for the runtime that serves FastAPI and `?view=TRADES`.
- [x] **IBKR Client Portal API**: Implemented as a fallback, but lower priority than the TWS socket.

#### Database & Storage
- [x] **Mongo Backup Automation**: Automate `mongodump` backups.
- [ ] **Google Docs/Drive Integration**: Define a strategy for storing non-code assets like blobs and spreadsheets in Google Drive.
- [ ] **Vector Database for RAG**:
    - [ ] Select and implement a vector database (ChromaDB, FAISS, etc.).
    - [ ] Build the ingestion pipeline for project documentation.

#### Deployment & Observability
- [ ] **Deployment Analysis**: Analyze cost/benefit of local vs. cloud Docker hosting.
- [ ] **Docker Hardening**: Secure containers with non-root users and proper secrets management.

---

### **Area: Algorithmic Intelligence & Analysis**

#### "Juicy" Opportunity Engine
- [ ] **Opportunity Lifecycle Tracking**: Create a `JuicyOpportunity` collection in Mongo to track, grade, and analyze the performance of generated opportunities.
- [x] **Opportunity Signals**: Detect uncovered stock positions (gap shares).
- [/] **Smart Roll / Diagonal Assistant**: Analyze expiring options to find optimal rolling strategies.
    - [x] Greeks calculation implemented using `py_vollib`.
    - [/] X-DIV (dividend) risk is incorporated.
    - [ ] **NEXT STEPS**: Implement Momentum Triggers and Gamma Penalties.
- [/] **Dividend Capture Strategy**:
    - [x] Scanner implemented to find dividend capture opportunities.
    - [x] UI created to list and analyze these opportunities.
    - [/] **Bugs**: Holdings, Predicted Price, and Target fields are sometimes empty.
- [ ] **UI Performance**: Ensure opportunity widgets read from the database and do not trigger blocking live scans.

#### Signal Generation & Strategy
- [/] **Markov Chains & Kalman Filters**:
    - [x] Research complete.
    - [x] Backend `SignalService` and API endpoint are implemented.
    - [/] **NEXT STEPS**: Integrate signals into the Smart Roll assistant and display them in the Ticker Modal.
- [/] **PRICE ACTION Analysis**:
    - [x] Research plan complete.
    - [/] Implement analysis of Market Structure (HH, HL) and Break of Structure (BOS).
    - [ ] Integrate signals into the UI.
- [ ] **News & Macro Trend Integration**:
    - [x] News API and sentiment analysis module implemented in the backend.
    - [/] Create an "Impact Score" for news events on portfolio tickers.
    - [ ] Integrate news sentiment into the Ticker Modal UI.

#### Backtesting & Research
- [ ] **Backtesting Engine**: Build an engine to back-play strategies against historical data.
- [ ] **Stock Research Agent**: Use Gemini AI to perform deep fundamental analysis on companies.

---

### **Area: Agentic AI & Advanced Features**

- [/] **Trading Agent**: Link from the portfolio grid to an agentic chat that is pre-loaded with the context of a specific position, allowing the user to ask "what should I do with this?"
- [ ] **Documentation RAG System**: Implement a chat interface to ask questions about the project's documentation and codebase.

---

## 3. Bugs & Maintenance
- [ ] **Stock Analysis Feature**: The entire feature stopped working after recent changes. Needs investigation. `[High Priority]`
- [ ] **1D NAV is Zero**: The 1-day NAV metric is often showing 0. This is likely due to a lack of intraday data points before the TWS service is fully operational.
- [/] **RT Trades Handshake Failure**: Clicking RT in Trades can currently report: `RT trades are unavailable. TCP socket is reachable, but the IBKR API handshake did not complete.` Treat this as a runtime/TWS API trust diagnostic issue first, then a trades UX issue second.
- [/] **Dividend Feed Bugs**: The holdings, predicted price, and target fields in the dividend feed are empty.

---
## 4. Project Governance

1.  **Decomposition**: Features should be broken down and elaborated. Create learning-opportunity or implementation-plan documents as needed.
2.  **Naming**: Use hierarchical IDs (e.g., `{feature_header}-{specific_feature_name}`).
3.  **Parallelism**: Note if tasks can be run by multiple agents concurrently.
4.  **Next Steps**: If a feature is not completed, the plan should include the next steps.
5.  **Cleanup**: If reviewing, add a "Review and Cleanup" section.

---

## 5. Changelog

| Date | Action | Reason |
| :--- | :--- | :--- |
| 2026-03-28 | **ADDED** | Created `CLAUDE.md` and updated `ARCHITECTURE.md`. |
| 2026-03-28 | **UPDATED** | Memorialized Stock Analysis ticker click popup implementation details. |
| 2026-03-25 | **UPDATED** | Trade History UI: Collapsed Trade Count widget to save vertical space. |
| 2026-03-21 | **REFACTORED**| Updated P&L logic to support account-aware FIFO matching. |
| 2026-03-21 | **ADDED** | Implemented per-account trade metrics widget in Trade History UI. |
| 2026-02-17 | **FIXED** | Fixed Dividend Scanner bug (method typo + expanded lookahead 0-30 days + UTC fix). |
| 2026-02-01 | **VARIOUS** | Initial refactoring, refinement, and feature additions by AI Agent. |
| 2026-03-31 | **UPDATED** | Added roadmap coverage for IBKR RT Trades handshake/runtime diagnostics and TWS trusted-client requirements. |
| 2026-03-31 | **UPDATED** | Added concrete `?view=PORTFOLIO` live-grid regression items for `undefined` values, missing option details, `STK`/`OPT` typing, and `NaN%` rendering. |
