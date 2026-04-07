# Stock Analysis — Ticker Click Feature Overview

> **Date:** 2026-03-28  
> **Status:** Partially Implemented (UI/Backend exist; sub-features incomplete)  
> **Parent Feature:** Stock Analysis UI (`features-requirements.md` §3 → Stock Analysis UI)

---

## What Happens When You Click a Ticker

When a user clicks any **ticker symbol** in the Stock Analysis grid (`StockGrid.jsx`), a full-screen modal (`TickerModal.jsx`) opens with **six tabbed views**, each pulling data from a dedicated backend API endpoint.

The modal header now includes:
- ticker linked to Google Finance
- company name/description linked to Yahoo Finance quote page
- normalized price and `%` change formatting
- explicit last-update timestamp text

### Data Flow

```
StockGrid.jsx  →  onClick triggers onTickerClick(ticker)
       │
       ▼
Dashboard.jsx  →  setSelectedTicker(ticker) → opens TickerModal
       │
       ▼
TickerModal.jsx  →  Parallel API fetches:
   ├── GET /api/ticker/{symbol}               → Analytics tab data
   ├── GET /api/opportunity/{symbol}           → Opportunity tab data
   ├── GET /api/portfolio/optimizer/{symbol}   → Optimizer tab data
   ├── GET /api/analysis/rolls/{symbol}        → Smart Rolls tab data
   └── GET /api/analysis/signals/{symbol}      → Signals tab data
```

### Entry Points

The ticker click works from **two grids**:

| Grid | Component | Context |
|:---|:---|:---|
| Stock Analysis | [StockGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/StockGrid.jsx) | Research view — all tracked tickers |
| My Portfolio | [PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/PortfolioGrid.jsx) | Portfolio view — held positions |
| Trade History | [TradeHistory.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TradeHistory.jsx) | Historical fills/dividends view |

### Symbol Resolution Hardening (2026-04-03)

- Portfolio and trade rows may contain option-like symbols or mixed formatting.
- Detail routing now canonicalizes to underlying equity symbols before opening `TickerModal`.
- Backend `GET /api/ticker/{symbol}` now performs:
  1. exact ticker match
  2. case/whitespace-insensitive fallback match
- Result: reduced false "No data found for this ticker." responses when data exists in local `stock_data`.

---

## Tab Descriptions

### 1. Analytics (Default Tab)
**API:** `GET /api/ticker/{symbol}`  
**Shows:** Price Action metrics (Current Price, 1D %, MA_50, MA_200, 52W High/Low) and Fundamentals (IV Rank, Implied Vol, Call/Put Skew, Div Yield, Market Cap, P/E).

### 2. Signals
**API:** `GET /api/analysis/signals/{symbol}`  
**Shows:** Kalman Filter trend analysis (signal, mean) and Markov Chain transition probabilities (current state, UP/DOWN probabilities). Includes a ROLL/HOLD recommendation with confidence percentage.  
**Learning:** [Kalman Filters](../learning/kalman-filters.md) | [Markov Chains & Signals](../learning/markov-chains-signals.md)

### 3. Opportunity
**API:** `GET /api/opportunity/{symbol}`  
**Shows:** Juicy Score (0-100 scale), positive Drivers, Risk Warnings, and metrics (IV Rank, Liquidity, Skew, RSI_14, ATR_14).  
**Learning:** [Opportunity Scoring](../learning/opportunity-scoring.md) | [Juicy Thresholds](../learning/juicy-thresholds.md) | [Bad Trade Heuristics](../learning/bad-trade-heuristics.md)

### 4. Optimizer
**API:** `GET /api/portfolio/optimizer/{symbol}`  
**Shows:** Ranked strategy suggestions (strategy name, action, reason, target strike) with "Analyze" buttons.

### 5. Price Action
**API:** `GET /api/ticker/{symbol}` (uses `Price Action` nested object)  
**Shows:** Trend direction (Bullish/Bearish), Market Structure points (HH, HL, LH, LL), Order Blocks, and Fair Value Gaps (FVGs).  
**Learning:** [Price Action Concepts](../learning/price-action-concepts.md) | [Implementation Plan](../plans/implementation_plan-20260202-price-action.md)

### 6. Smart Rolls (Conditional)
**API:** `GET /api/analysis/rolls/{symbol}`  
**Visible only when:** roll data exists for this ticker (held positions with open options).  
**Shows:** Roll suggestions with score, net credit, static yield, UP return, total yield, and dividend risk warnings.  
**Learning:** [Smart Roll & Diagonal Strategy](../learning/smart-roll-diagonal.md) | [X-DIV Rolling](../learning/x-div-rolling.md)

---

## Key Source Files

| File | Role |
|:---|:---|
| [TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx) | Main modal component — 6 tabs, parallel data fetching |
| [StockGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/StockGrid.jsx) | Analysis grid — ticker link renderer with click handler |
| [PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/PortfolioGrid.jsx) | Portfolio grid — ticker click opens same modal |
| [Dashboard.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/Dashboard.jsx) | Parent — manages `selectedTicker` state, renders `TickerModal` |
| [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py) | Backend API — all 5 ticker endpoints |
| [stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py) | Backend — computes ~40 metrics per ticker |

---

## Related Documentation

### Learning Docs
- [Moving Averages (SMA/EMA/HMA/TSMOM)](../learning/Moving_Averages_for_Stock_Value_Analysis.md) — Trend/value strategy
- [Greeks Data Ingestion](../learning/greeks-data-ingestion.md) — Black-Scholes Greeks calculation
- [Greeks Expiration Filters](../learning/greeks-expiration-filters.md) — Filtering by expiration + Greeks
- [Opportunity Scoring](../learning/opportunity-scoring.md) — 0-100 scoring rubric
- [Juicy Thresholds](../learning/juicy-thresholds.md) — IV Rank > 50, Delta 0.3-0.4 limits
- [Kalman Filters](../learning/kalman-filters.md) — Mean reversion / trend following
- [Markov Chains & Signals](../learning/markov-chains-signals.md) — State transition predictions
- [Price Action Concepts](../learning/price-action-concepts.md) — HH/HL/LH/LL, BOS, FVG, Order Blocks
- [Smart Roll & Diagonal Strategy](../learning/smart-roll-diagonal.md) — Roll heuristics
- [Bad Trade Heuristics](../learning/bad-trade-heuristics.md) — Patterns to block

### Implementation Plans
- [Analysis Signals](../plans/implementation_plan-20260201-analysis-signals.md)
- [Analysis Signals Refinement](../plans/implementation_plan-20260202-analysis_signals_refinement.md)
- [Juicy Finder](../plans/implementation_plan-20260202-juicy-finder.md)
- [Juicy Opportunity Backend](../plans/implementation_plan-20260202-juicy_opportunity_backend.md)
- [Smart Roll Assistant](../plans/implementation_plan-20260202-smart_roll_assistant.md)
- [Smart Roll UI](../plans/implementation_plan-20260202-smart_roll_ui.md)
- [Smart Roll & Markov Integration](../plans/implementation_plan-20260203-smart_roll_markov.md)
- [Price Action](../plans/implementation_plan-20260202-price-action.md)
- [Greeks Integration](../plans/implementation_plan-20260202-greeks_integration.md)
- [Markov Chains](../plans/implementation_plan-20260203-markov_chains.md)

### Feature Docs
- [Stock Analysis Feature Recap](stock_analysis_feature_recap.md) — Bug investigation & data flow architecture
- [SMA/EMA/HMA/TSMOM Strategy Guide](SMA-EMA-HMA-TSMON.md) — Technical indicator strategy

### Walkthroughs
- [Greeks Integration Walkthrough](../plans/walkthrough-20260202-greeks_integration.md)
- [Smart Roll Assistant Walkthrough](../plans/walkthrough-smart_roll_assistant.md)
- [Markov Chains Walkthrough](../plans/walkthrough-markov_chains.md)

---

## Outstanding Work (TODO)

These items from `features-requirements.md` remain incomplete:

1. **Tickers — Composite Rating**: Aggregate all metrics (momentum, Call/Put Skew, news sentiment, technicals) into a single "Ticker Health" score displayed in the grid. *(Not yet implemented)*
2. **Stock Analysis — All Data in Popup**: The TickerModal currently shows a subset; all ~40 columns from the analysis should be surfaced in the Analytics tab.
3. **Stock Analysis — Analytics Sub-tab**: Deeper drill into technical analysis (IV surface, Greeks heatmap, historical metrics).
4. **Stock Analysis — Signals Sub-tab**: Expand with news sentiment signals and macro impact scoring.
5. **Stock Analysis — Opportunities Sub-tab**: Surface Buy/Sell recommendations, dividend capture, and covered call candidates.
6. **Stock Analysis — Optimizer Sub-tab**: Multi-leg strategy optimizer with risk/reward visualization.
7. **Stock Analysis — Price Action Sub-tab**: Add interactive charting with ZigZag overlay, supply/demand zone visualization.

---

---

## Degraded-State UX — Per-Tab Error Badges

When a tab endpoint fails (timeout, network error, HTTP 4xx/5xx) or the browser is offline, the tab body renders a compact inline reason badge instead of a silently empty section.

### Reason Codes and Badge Text

| Reason | Trigger | Badge Text |
|:---|:---|:---|
| `timeout` | axios `ECONNABORTED`, message contains "timeout", or watchdog exit with no error | `Timed out — data unavailable` |
| `offline` | `navigator.onLine === false` at fetch time | `Offline — no network` |
| `endpoint` | HTTP 4xx/5xx, `Network Error`, `ECONNREFUSED`, `failed to fetch` | `Endpoint unavailable` |
| `stale` | Explicit stale-cache path (reserved for future use) | `Showing cached data` |

### Architecture

- **`tickerModalResilience.js`** — Pure-function module exporting `classifyTabError(isOffline, error)` and `getBadgeText(reason)`. Kept separate from the React component for `node:test` unit testability.
- **`TickerModal.jsx`** — Adds `tabErrorReasons` state (per-tab, mirrors `tabLoadState`). `fetchTabData` catches errors, calls `classifyTabError`, stores the reason. `renderTabPanel` checks `state === 'error'` and renders `TabErrorBadge` with the stored reason.
- **`TabErrorBadge`** — Minimal React component: amber text, dark background, `AlertTriangle` icon, dark-theme compatible. Renders `data-testid="tab-error-badge"` and `data-reason` attributes for testing.

### Invariants

- A failed tab badge does NOT affect other tabs — each tab's error reason is independent.
- Successful tabs always render their data view as before.
- The badge replaces the tab content (not an overlay or modal-level error).
- `tabErrorReasons` is reset to `null` for all tabs on ticker change/modal open.

---

## Changelog

| Date | Action | Reason |
|:---|:---|:---|
| 2026-03-28 | **CREATED** | Initial feature overview documenting existing ticker click behavior, data flow, tabs, API endpoints, and all related docs |
| 2026-04-02 | **UPDATED** | Header enrichment completed in `TickerModal`: ticker/descriptive link targets, `%` formatting fix, and last-update normalization with utility tests |
| 2026-04-03 | **UPDATED** | Detail-loading reliability hardening: canonical ticker routing from Portfolio/Trades and backend relaxed ticker lookup fallback for local DB resolution |
| 2026-04-07 | **UPDATED** | resilience-004/005: per-tab degraded reason badges (`TabErrorBadge`, `tickerModalResilience.js`) and regression tests (`tickerModalResilience.test.js`) |
