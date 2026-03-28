# Juicy Fruit Stock Options — Claude Code Workspace

## Project Overview
**"Juicy Fruit"** is a semi-automated trading dashboard for **Trader Ken** (Ken MacPherson), supporting covered calls, wheel strategy, dividend capture, and options analysis across 3 IBKR accounts. ~25+ years of active trading experience.

- **Backend**: FastAPI (Python) + MongoDB + APScheduler
- **Frontend**: React (Vite) + dark theme data-dense UI
- **Data Sources**: IBKR Flex Reports, Yahoo Finance (`yfinance`), NewsAPI, FRED API
- **Infrastructure**: Docker Compose (app + mongo services)

---

## Key Rules — Read Before Writing Code

### Workflow
1. Read `.agent/workflows/create-a-plan.md` before any non-trivial implementation.
2. Follow `.agent/rules/document.md` for all documentation changes.
3. Trading logic rules are in `.agent/rules/trader-ken.md`.
4. Mark items in `docs/features-requirements.md` as `[/]` (In Progress) immediately when starting work.
5. Always create/update `docs/features/{feature_name}.md` for feature work.
6. Save implementation plans to `docs/plans/implementation_plan-YYYYMMDD-short_name.md`.
7. **Pause and get user approval** before executing any implementation plan.

### Code Standards
- **Logging**: All backend logs prefixed `{datetime} - {filename-class-method} - {LEVEL} - {message}`. Use `app/utils/logging_config.py`.
- **Testing**: Always write tests. Run `pytest`. Follow `.agent/workflows/test-coverage.md`.
- **Typing**: Pydantic models for all data shapes. Strong typing throughout.
- **Single Responsibility**: Each service has one job. No business logic in routes.
- **MongoDB**: Single source of truth. Raw data in collections; computed views at query time.
- **Security**: OWASP top-10 awareness. Input validation at all API boundaries. No hardcoded secrets.

### UI/UX Standards (Juicy Fruit)
- **Density over Fluff**: Data tables and metrics, not large buttons or empty space.
- **Yield-First**: Every opportunity must display Annualized Yield % and Total Potential Return.
- **No Floating Modals for Core Data**: Use expandable Detail Drawer (right side) to maintain context.
- **Dark theme** throughout.

---

## Project Structure

```
juicyfruitstockoptions/
├── CLAUDE.md                         # ← Claude Code workspace config (this file)
├── ARCHITECTURE.md                   # High-level architecture + file tree
├── DEPENDENCY_GRAPH.md
├── README.md
├── requirements.txt                  # Python dependencies
├── docker-compose.yml
├── Dockerfile
│
├── app/                              # Python FastAPI backend
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Pydantic settings (env vars)
│   ├── database.py                   # MongoDB connection
│   ├── jobs.py                       # Top-level job triggers
│   ├── api/
│   │   ├── routes.py                 # All REST endpoints (~1400 lines)
│   │   └── trades.py                 # Trade history endpoints
│   ├── auth/
│   │   ├── dependencies.py           # FastAPI auth dependencies
│   │   ├── users.py                  # User management
│   │   └── utils.py                  # JWT helpers
│   ├── models/
│   │   └── opportunity.py            # JuicyOpportunity Pydantic model
│   ├── scheduler/
│   │   └── jobs.py                   # APScheduler job definitions
│   ├── scripts/                      # One-off admin/migration scripts
│   ├── services/                     # Business logic layer
│   │   ├── dividend_scanner.py       # Dividend capture + ICS calendar
│   │   ├── expiration_scanner.py     # Options expiring <N days
│   │   ├── export_service.py         # CSV/XLSX export
│   │   ├── ibkr_service.py           # IBKR Flex Report parsing + sync
│   │   ├── llm_service.py            # Gemini/LLM integration
│   │   ├── macro_service.py          # FRED macro indicators
│   │   ├── news_service.py           # NewsAPI aggregation + sentiment
│   │   ├── opportunity_service.py    # Opportunity persistence + grading
│   │   ├── options_analysis.py       # Core options analysis (OptionsAnalyzer)
│   │   ├── pnl_calculator.py         # P&L + cost basis FIFO
│   │   ├── portfolio_analysis.py     # Portfolio enrichment + NAV
│   │   ├── price_action_service.py   # ZigZag, BOS, FVG, Order Blocks
│   │   ├── risk_service.py           # Position risk guardrails
│   │   ├── roll_service.py           # Smart Roll + Greeks integration
│   │   ├── scanner_service.py        # Master scanner orchestration
│   │   ├── sentiment_service.py      # NLP sentiment (NLTK/transformers)
│   │   ├── signal_service.py         # Kalman + Markov signal generation
│   │   ├── stock_live_comparison.py  # Live ticker analysis engine
│   │   ├── ticker_discovery.py       # New ticker discovery
│   │   └── trade_analysis.py         # Trade history analytics
│   └── utils/
│       ├── excel_exporter.py         # XLSX report builder
│       ├── greeks_calculator.py      # Black-Scholes Greeks (py_vollib)
│       ├── logging_config.py         # Centralized logging setup
│       └── mongo_client.py           # MongoDB client helpers
│
├── frontend/                         # React (Vite) frontend
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── context/
│       │   └── AuthContext.jsx
│       ├── components/
│       │   ├── AlertsDashboard.jsx
│       │   ├── Dashboard.jsx         # Main dashboard + routing
│       │   ├── DividendAnalysisModal.jsx
│       │   ├── DividendListModal.jsx
│       │   ├── DividendScanner.jsx
│       │   ├── Login.jsx
│       │   ├── NAVStats.jsx          # Portfolio KPI widgets
│       │   ├── PortfolioGrid.jsx     # Portfolio positions table
│       │   ├── RollAnalysisModal.jsx
│       │   ├── SettingsModal.jsx
│       │   ├── StockGrid.jsx         # Stock analysis table
│       │   ├── TickerModal.jsx       # 6-tab ticker detail modal
│       │   └── TradeHistory.jsx      # Trade history + metrics
│       └── utils/
│           └── downloadHelper.js
│
├── tests/                            # pytest test suite (~60+ test files)
├── docs/
│   ├── features-requirements.md      # Master PRD / Kanban (source of truth)
│   ├── features/                     # Feature detail docs
│   │   ├── stock_analysis_ticker_click.md
│   │   ├── stock_analysis_feature_recap.md
│   │   ├── SMA-EMA-HMA-TSMON.md
│   │   ├── legacy_trade_ingestion.md
│   │   ├── trade_history_analysis.md
│   │   ├── Ticker_Protection_and_Discovery.md
│   │   ├── automated_mongo_backup.md
│   │   └── UI-UX Overhaul/
│   ├── learning/                     # Domain knowledge docs
│   └── plans/                        # Implementation plans (YYYYMMDD naming)
│
├── .agent/
│   ├── rules/
│   │   ├── document.md               # Documentation standards
│   │   └── trader-ken.md             # Trading logic / domain rules
│   └── workflows/
│       ├── create-a-plan.md          # Implementation planning checklist
│       ├── learing-opportunity.md    # Learning doc workflow
│       ├── test-coverage.md          # Test standards
│       └── misson.md                 # Project mission
│
├── .github/                          # GitHub Actions / PR templates
├── report-results/                   # Generated XLSX reports (gitignored)
├── xdivs/                            # Generated ICS calendar files
├── scripts/                          # Shell/Python utility scripts
├── stock_live_comparison.py          # Standalone stock analysis runner
└── Ai_Stock_Database.py              # Legacy stock DB script
```

---

## MongoDB Collections (stock_analysis DB)

| Collection | Purpose |
|---|---|
| `ibkr_holdings` | Live portfolio positions (synced from IBKR) |
| `opportunities` | All detected trading opportunities |
| `corporate_events` | Earnings + ex-div calendar events |
| `stock_data` | Ticker analysis data (used by TickerModal) |
| `system_config` | App configuration / settings |
| `nav_history` | Historical NAV performance |
| `trades` | Trade history (ingested from IBKR Flex) |
| `dividends` | Dividend history (in progress) |

---

## Common Commands

```bash
# Start full stack
docker-compose up --build

# Run backend only (dev)
uvicorn app.main:app --reload --port 8000

# Run frontend (dev)
cd frontend && npm run dev

# Run tests
pytest

# Run specific test file
pytest tests/test_roll_service.py -v

# Stock live analysis (standalone)
python stock_live_comparison.py
```

---

## Environment Variables (`.env`)
```
MONGO_URI=mongodb://localhost:27017
SECRET_KEY=<jwt-secret>
GOOGLE_API_KEY=<gemini-api-key>
NEWS_API_KEY=<newsapi-key>
FRED_API_KEY=<fred-api-key>
IBKR_FLEX_TOKEN=<ibkr-flex-token>
```

---

## References
- Master PRD: [docs/features-requirements.md](docs/features-requirements.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Trading Rules: [.agent/rules/trader-ken.md](.agent/rules/trader-ken.md)
- Plan Workflow: [.agent/workflows/create-a-plan.md](.agent/workflows/create-a-plan.md)
