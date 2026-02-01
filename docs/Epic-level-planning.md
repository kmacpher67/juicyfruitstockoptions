# Epic-Level Planning & Roadmap

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
-- The implementation plan should be created using google antigravity
-- The incremental implementation plan should follow hierarchical decomposition for naming based the short name of the epic (e.g., epic-001-algorithmic-trading-001-task-001)

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
- [ ] **Google Docs Migration**: define rules/plans to store non-code docs (blobs, excel) in Google Docs vs Info storage.
- [ ] **RAG System (Documentation)**: Implement RAG (Retrieval-Augmented Generation) for asking questions about the codebase/docs.

### Deployment & Security
- [ ] **Local vs Cloud Analysis**:
    - [ ] Analyze cost/benefit of running Docker on Home PC vs Cloud (AWS/GCP/DigitalOcean).
    - [ ] Identify headache factors (latency, maintenance).
- [ ] **Docker Hardening**: Secure containers when exposed to the internet (ports, user permissions, secrets).
- [ ] **Authentication**:
    - [ ] Auto-logout UI if backend token expires.
    - [ ] Synced session state between generic React usage and Python backend.
- [ ] **Settings Management**:
    - [ ] Admin defaults vs User overrides.
    - [ ] Enforce "minimum safe settings" that users cannot override.

### Data Reliability
- [ ] **Mongo Backup Automation**:
    - [ ] Automate backup to GitHub (current manual process).
    - [ ] Investigate Google Drive as alternative storage.
    - [ ] *Action*: Have agent follow `learning-opportunity.md` to recommend best backup practices.
- [ ] **TWS API container**: Evaluate need for a dedicated TWS API Docker container for stable IBKR connection, and create more epic items as neccessary. 

---

## 3. Algorithmic Trading Engines (Epic 2)
**Owner:** Ken | **Goal:** Automated insights and strategy backtesting.

### Portfolio Management
- [ ] **Portfolio Management**: Get entire history of portfolio performance
- [ ] **Portfolio Management**: Get entire history of trades (ie: with cost basis) and all relevant metrics

### Analysis & Signals
- [ ] **"Juicy" Opportunity Finder**:
    - [ ] Screen for covered call candidates (high premiums, stable/upward trend).
    - [ ] Screen for call buying opportunities (momentum).
    - [ ] Strategy: Use "Juicy Calls" premium to fund downward protection (puts) or long calls.
- [ ] **Targeting Logic**: Integrate Macro trends and News events into the analysis and portfolio views. 
- [ ] **Kalman Filters**: Implement Kalman filters for signal generation.

### Strategy & Backtesting
- [ ] **Backtesting Engine**:
    - [ ] Ability to "back play" strategies using historical IBKR data.
    - [ ] Evaluate libraries: Zipline, VectorBT, or custom.
- [ ] **Metric Stack**: Implement standard metrics: Sharpe, Sortino, MaxDD, Hit-rate, Turnover.
- [ ] **Personal Trading History**:
    - [ ] Build history of Ken's previous trades.
    - [ ] Analyze performance of past trades to derive a personalized strategy.
    - [ ] **RAG for Trading History**: Chat with past trading data.

### ML in the Loop (8-Step Flow)
- [ ] **Universe Selection**: Define the pool of tradeable assets. Find new juicy fruit candidates based on macro trends, news events, and quant analysis.
- [ ] **Feature Engineering**: Momentum, Quality, Volatility factors.
- [ ] **Time-Series CV**: rigorous cross-validation without look-ahead bias (leakage).
- [ ] **Model Training**: Implementation (e.g., XGBoost, Scikit-learn).
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
- [ ] **Yield Analysis**: Visuals for Yield vs Cost Basis vs ROI.

### Scheduler Management (UI)
- [ ] **Control Panel**:
    - [ ] Pause / Stop Scheduler.
    - [ ] Resume Scheduler.
    - [ ] View Scheduler Logs (live stream?).
    - [ ] View Scheduler Status/Health.
    - [ ] View/Edit Scheduler Config/History.

### Help & Onboarding
- [ ] **Contextual Hints**: Hover tooltips explaining formulas/metrics.
- [ ] **AI Chatbot Integration**: Side-panel chat to answer questions about dashboard data.
- [ ] **Data Helper**: Explains why an asset is juicy fruit, opportunity, or current focused financial item's status. 

---

## 5. Agentic AI & Intelligence (Epic 4)
**Owner:** Antigravity Data | **Goal:** Force multiplication via AI agents.

### Capabilities
- [ ] **Prototype Agent**:
    - [ ] Juicy Fruit Opportunity Finder for a given stock or option (diagonal spread or close position (stop loss or take advantage of momentum), or keep to expiration).
    - [ ] 
- [ ] **Local Model Hosting**:
    - [ ] Evaluate robust local LLMs (Llama 3, Mistral) vs Cloud APIs.
    - [ ] Hardware requirements vs Cost.
- [ ] **Framework Prototype**:
    - [ ] Create simple "Stock Market Chatbot" using LangChain + OpenAI.
    - [ ] Test RAG capabilities on `docs/`.
- [ ] **Tooling Research**:
    - [ ] Scikit-learn: Best practices for this specific project?
    - [ ] MLflow: Is it overkill or necessary for experiment tracking?

---

## 6. Risk Management & Safety (Epic 5)
**Owner:** Risk Officer | **Goal:** Protect capital.

- [ ] **Guardrails**:
    - [ ] **Position Limits**: Max allocation per ticker/sector.
    - [ ] **Slippage Control**: Warnings for illiquid options.
    - [ ] **Stop Rules**: Auto-exit criteria.
    - [ ] **"Ken's Bad Trades"**: Specific heuristic to detect and block historically poor impulsive setups.

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
| 2026-02-01 | **REFACTORED** | Initial full cleanup and organization into Epics by AI Agent. |
| 2026-02-01 | **DELETED** | Removed "initial draft" placeholder text. |