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
    - [ ] IBApi The official API for Interactive Brokers provides access to all the data available through IB. Replaces IBPy. interactivebrokers.github.io/tws-api/
    


### Observability & Logging
- [/] **Logging**: Implement logging for all backend services.  
    - [x] Implement detailed DEBUG - **Style:** preface all logs with "{datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}"    the message text should tell the user what is happening (if possible, include the result of the action)
- [ ] **Logging**: Implement logging for all frontend services. 
    - [ ] Research centralized logging (e.g., sending frontend logs to backend API).
    - [ ] Implement React Error Boundary logging. 
- [x] **Structured Logging:** Use the standard `logging` library.
- [x] **Levels:** `DEBUG` (internal state), `INFO` (milestones), `ERROR` (exceptions with `exc_info=True`).
- [ ] **Levels:** `TRACE` for verbose logging of internal state, `WARNING` for non-critical issues, `ERROR` for critical issues. `CRITICAL` for system failure. 
- [ ] **Traceability:** Verify all errors provide context (e.g., "Failed to process file X due to Y").

---

## 3. Algorithmic Trading Engines (Epic 2)
**Owner:** Ken | **Goal:** Automated insights and strategy backtesting.


### Stock Analysis UI
- [x] **Stock Analysis**: Ticker list research grades averages and creates a .xlsx report for download of Call/Put Skew. 
- [x] **Stock Analysis**: Run Live Analsis runs the live analysis of a ticker list updates the list.
    - [x] **Run Live Analysis**: Disables button while analysis is running. Changes to "running" until ready again, reloads the grid.
    - [ ] **Run Live Analysis**: Create/Add, Delete, Update Ticker List. 
    - [x] **Portfolio items**: Disable the Delete button for portfolio items so they stay persistant, maintain security of the portfolio for other non users, don't reveal any additional sensitive information.
    - [ ] **Tickers**: Based on all the metrics of the ticker, news, momentum, call skew,  

### Portfolio Management UI
- [/] **Portfolio Analytics**: Show Key Performance Indicators (NAV, d/w/m/y changes) on the Portfolio Dashboard (via `NAVStats`).
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
- [ ] **My Portfolio** Window screen size seems smaller than the analysis page causing the grid to have to horizontally scroll.  Can we increase the size of the screen size of the My Portfolio page to match the analysis page or the size of the screen, we have plenty of extra room. What's logical given we are going to be adding features and ui stuff?  

- [x] **Trade History Management**: Get entire history of trades (ie: with cost basis) and all relevant metrics
    - [x] Ingest Legacy Trade Files (See [Legacy Trade Ingestion](features/legacy_trade_ingestion.md))
    - [x] **Backend API**: Create `/api/trades` endpoint to serve historical data with pagination/filtering.
    - [x] **Business Logic**: Implement Cost Basis and Realized P&L calculation (grouping buys/sells by symbol).
    - [x] **Frontend**: Build "Trade History" view with datagrid, filtering, and export.
    - [x] **Metrics**: Add summary metrics (Total P&L, Win Rate, LT/ST P&L, etc.) to the history view.
    - [x] **Bug issue**: History view is not loading trades, 500 Internal Server Error http://localhost:3000/api/trades/analysis
    - [x] **Bug issue**: Portfolio view sub menu is dropping down when going to the trades menu tab. 
    - [x] **Trade Metrics Education**: See [Trade Metrics Guide](learning/trade-metrics.md). Explains Win Rate, Profit Factor, Diagonal Rolls, and Dividends.
    - [ ] **time window**: For trade history view, can we implement a time window starting with MTD, having 1D, 1W, 1M, 3M, 6M, 1Y, 5Y,and All trades?

### Analysis & Signals
- [ ] **"Juicy" Opportunity Finder**:
    - [/] **Juicy Opportunity Collection**: Implement full lifecycle tracking for detected opportunities. Allows complex long running processes to be only run once and the results persisted to be used for other features. 
        - [x] **Data Schema**: Define `JuicyOpportunity` model (Symbol, Timestamp, Context: {Price, IV, Greeks}, Proposal, Trigger Source).
        - [x] **Persistence**: Store opportunities in MongoDB (`opportunities` collection) for historical analysis.
        - [ ] **Outcome Tracking (Truth Engine)**:
            - [ ] **Requirement**: Automated tracker that monitors the specific option/stock for the duration of the proposed trade.
            - [ ] **Metrics**: Max Profit (MFE), Max Loss (MAE), Days to Profit, Expiration Value.
            - [ ] **Reference**: See [Opportunity Persistence & Grading](learning/opportunity-persistence-and-grading.md).
        - [ ] **Grading Engine**: Scheduled job to close and grade opportunities (Win/Loss, ROI/Day) based on market data.
        - [ ] **Signal Correlation**: Dashboard to analyze Hit Rate by Signal Source (e.g., "Do Gap Ups work?"). 
        - [x] **Options Due in X Days**: Signal for all options expiring in <7 Days (DTE). *Backend Implemented via `ExpirationScanner`.*
        - [/] **X-DTE options UI**: Only show the DTE<7 list of options so they can be evaluated for rolling, holding, waiting, or closing. Leave space for showing greeks, probability, payouts, Returns, yields, LT vs ST P&L, create UX for showing opportunties available for rolling, holding, waiting, or closing. See [Implementation Plan](plans/implementation_plan-20260203-xdte_autoroll.md).
        - [/] **Auto-Roll Evaluation**: Automatically analyze rolling opportunities for these positions (e.g., Roll to next week or month if covered call is ITM). See [Implementation Plan](plans/implementation_plan-20260203-xdte_autoroll.md).
        - [x] **Auto-Roll Fixes**: The roll doesn't show the yield and the return. It's unclear what the original ticker OPT details are it's MSFT put or call. Original strike price is unknown. Time of the original contract and return / yield is unknow. What about the whole sequence of that buy and sell? What part makes money? Under what scenario (price change Up/Down, time change, yield change) does it make money? 
        - [x] **Auto-Roll Fixes**: What does the SELECT button do? **Definition**: Clicking "Select" logs the chosen roll strategy (Buy to Close Current + Sell to Open New) and provides a "Success" toast notification. Future state will persist this to a Trade Plan or trigger an IBKR Order ticket.
        - [x] **Auto-Roll Fixes**: The "Dividend Capture Opportunities" button is huge and empty which is not a good user experience.
        - [x] **Auto-Roll Fixes**: After clicking on a roll there is spinner as it's thinking. Do these Smart Roll Analysis get saved somewhere?  
        - [x] **Auto-Roll Fixes**: No suitable rolls found for this position. Misses the point, WAIT, HOLD, or CLOSE. Are options also? If there are no suitable rolls found for this position, is the XDTE only offer a roll? 
   
        - [x] **Scheduler Integration**: Scans scheduled every 30 mins (Market Hours) and 1 hr Pre/Post-Market.
        - [x] **UI Performance**: UI components (e.g., Dividend Capture) must read from DB persistence, NOT trigger blocking live scans.  
    - [ ] **Heuristic Checklist for Your Dashboard**; Pattern, Detection Logic, Risk Type referenced in docs/learning/bad-trade-heuristics.md
    - [x] **Opportunity Signals**: Detect and alert on uncovered stock positions (gap shares) suitable for covered calls (displayed as "Opp Block" in Portfolio view).
    - [x] **Bug issue**: MRVL Gap 500 Shares, Trend UP (+0.12%) but it's not up in recent trading. **Fixed**: Corrected parsing of "1D % Change" in OptionsAnalyzer and fixed scoring logic for trend.
    - [x] **Opportunity Scoring Rubric**: See [Opportunity Scoring](learning/opportunity-scoring.md). Defines the 0-100 rating scale and factors (IV, Trend, Liquidity). 
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
            - [x] **x-div**: export a .ics list and details for calendar integration (copy and paste into google calendar). implemented `/api/calendar/dividends.ics`.
        - [ ] **Scoring**: Factor in underlying stock profit (increase in strike width), cost to close, and premiums of new strikes.
        - [x] **strategy**: Find suitable Roll Calendar/Diagonal with favorable Return and Yield. Consider position move to more profit (unrealized stock gain) vs cost of buyback. Prefer near 0DTE or short term if profitable, incorporate all the strategies available to make recommendations or opportunities on the portfolio.
        - [x] **Add to UI**: Incorporate into the app.
            - [x] **Smart Roll Widget**: In `TickerModal` (for held positions) and `PortfolioGrid` (overview). Display score, net credit, and "Dividend Risk" warnings.
            - [x] **Dividend Capture List**: New section in `Dashboard` or modal to display logic from `/api/analysis/dividend-capture`.
            - [x] **Calendar Export**: Button in `PortfolioGrid` (via Dashboard Dropdown) to download `.ics` file.
        - [x] **Smart Roll Strategy**: See [Smart Roll & Diagonal Strategy](learning/smart-roll-diagonal.md). Defines heuristics for Short Duration (<10 days), Credit Priority, and Strike Improvement.
    - [x] Screen for call buying opportunities (momentum).
    - [ ] Strategy: Use "Juicy Calls" premium to fund downward protection (puts) or long calls. Add this to the opportunity finder section of the ticker modal and the portfolio view.
    - [x] **Juicy Thresholds**: See [Juicy Thresholds](learning/juicy-thresholds.md). Defines quantitative limits (IV Rank > 50, Delta 0.3-0.4).
    - [x] Implement Scanners/Screeners module in Python.
- [ ] **Targeting Logic**: Integrate Macro trends and News events into the analysis and portfolio views.
    - [x] Integrate external News API (e.g., NewsAPI.org). *Backend Implemented*
    - [x] Build a News Aggregator to fetch news events and store them in a database. *Backend Implemented*
    - [/] **News headlines and Senitiments**: stored with Logic/Reasoning. *UI Pending*. similar to "Sea Limited (SE)..."
        - [x] **Data Structure**: Enforce strict JSON output with `logic`, `reasoning`, `impact_window`, and `opportunity_score`.
        - [x] **Validation**: Ensure "Sea Limited" example case is strictly reproducible. 
    - [x] **Sentiment**: write a sentiment analysis module using `transformers` or `nltk`. 
        - [x] **Heuristics**: Implement "Logic Check" (Stage 1) to assign Short/Long term impact based on keywords.
        - [ ] **Future LLM**: Prepare hook for Gemini/LLM to generate natural language `reasoning`. 
    - [x] **Sentiment**: write a learning features document for sentiment and headlines  .agent/workflows/learing-opportunity.md Same or extra doc as here: @features-requirements.md#L163 
    - [x] Fetch Macro indicators (Fred API). *Backend Implemented*
    - [/] Create "Impact Score" for news events on portfolio tickers. *Logic Implemented, UI Pending*
        - [ ] **Research**: Evaluate X (Twitter) API v2 Basic Tier (~$100/mo) vs Free Limits for "Alpha Lists".
        - [ ] **Research**: Investigate Yahoo Scout integration (Scraping vs User Manual Copy/Paste).
    - [x] **Learning Opportunity**: - using the  .agent/workflows/learing-opportunity.md write a learning doc about how to LMM and target macro trends and news events in our trading. 
- [ ] **Markov Chains**: Implement Markov Chains for signal generation and proposed strategies like rolls vs holding for a given OPT and it's underlying stock. 
    - [ ] Research `markovify` or `pykalman` libraries.
    - [ ] Prototype Mean Reversion and Trend Following models using Kalman.
    - [ ] **Learning Opportunity**: - using the  .agent/workflows/learing-opportunity.md write a learning doc about how to use Markov Chains for signal generation and proposed strategies like rolls vs holding for a given OPT and it's underlying stock.  How does this work with Kalman filters, pros and cons, what's better for what scenario.  How to use this to generate signals for the portfolio.  Recommend next steps and update feature-requirements.md lists for Markov chains as needed.
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

## 6. Risk Management & Safety (Epic 5)
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
**Rules for Agents working on this Epic:**
1.  **Decomposition**: Evaluate features and requirements, elaborate them, make sure if required add a new feature/requirement to generate a learning-opportunity or implementation-plan document. That fits into the context window of the technical limitations of the LLM and the project. Add questions or highlight to the user for feedback as needed. 
2.  **Naming**: Use hierarchical IDs (e.g., `epic-001-trading-001-task-001`).
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