# Stock Analysis — Profile Tab

## Summary
Add a **Profile** sub-tab to `TickerModal` that surfaces company profile data and recent news sourced from `yfinance`. Profile data is refreshed when the user clicks **Run Live Comparison** or automatically at the configured daily schedule time.

## User Story
> As Trader Ken, when I open a ticker in the modal I want a Profile tab that gives me a quick company overview — sector, industry, style, description, key fundamentals ratios, analyst consensus, and recent news headlines — so I can assess fit with my covered call / wheel strategy without leaving the app.

---

## Refresh Cadence
Profile data is stored in the `stock_data` collection under a `profile` sub-document.

| Trigger | Mechanism |
|---|---|
| **Run Live Comparison** (manual button) | `fetch_ticker_record()` in `stock_live_comparison.py` populates `profile` as part of each ticker record during the run |
| **Daily schedule** | Same job runs at the configured `hour:minute` in `system_config` via APScheduler |
| **Lazy hydration** (fallback) | If `profile` is absent when `/ticker/{symbol}` is called, the endpoint fetches from yfinance and backfills to DB |

---

## Data Fields

### Company Identity (from `yf.Ticker.info`)

| Display Name       | yfinance key              | Notes                                      |
|--------------------|---------------------------|--------------------------------------------|
| Description        | `longBusinessSummary`     | Truncated with expand toggle               |
| Sector             | `sector`                  |                                            |
| Industry           | `industry`                |                                            |
| Style / Type       | `quoteType` + `category`  | "EQUITY", "ETF", ETF category if available |
| Exchange           | `exchange`                |                                            |
| Country            | `country`                 |                                            |
| Employees          | `fullTimeEmployees`       | Formatted with commas                      |
| Website            | `website`                 | Clickable external link                    |

### Analyst & Fundamentals Snapshot (from `yf.Ticker.info`)

| Display Name            | yfinance key                | Notes                        |
|-------------------------|-----------------------------|------------------------------|
| Analyst Recommendation  | `recommendationKey`         | buy / hold / sell badge      |
| # Analyst Opinions      | `numberOfAnalystOpinions`   |                              |
| Beta                    | `beta`                      | Volatility vs market         |
| Forward P/E             | `forwardPE`                 |                              |
| Price to Book           | `priceToBook`               |                              |
| Return on Equity        | `returnOnEquity`            | % formatted                  |
| Debt to Equity          | `debtToEquity`              |                              |
| Earnings Growth (YoY)   | `earningsGrowth`            | % formatted — growth signal  |
| Revenue Growth (YoY)    | `revenueGrowth`             | % formatted                  |

### Recent News (from `yf.Ticker.news`)
- Up to **5 most recent headlines** (title, publisher, date, link)
- Each headline links to the article (`_blank`)
- Bottom of the tab links to **Yahoo Finance News** page for the ticker

---

## Backend Changes

### `stock_live_comparison.py` — `fetch_ticker_record()`
Add `profile` sub-document to each ticker record using already-available `info` dict and a separate `tickers_obj.tickers[t].news` call:
```python
record["profile"] = {
    "sector": info.get("sector", ""),
    "industry": info.get("industry", ""),
    "description": info.get("longBusinessSummary", ""),
    "style": info.get("quoteType", ""),
    "category": info.get("category", ""),
    "exchange": info.get("exchange", ""),
    "country": info.get("country", ""),
    "employees": info.get("fullTimeEmployees"),
    "website": info.get("website", ""),
    "recommendation": info.get("recommendationKey", ""),
    "analyst_opinions": info.get("numberOfAnalystOpinions"),
    "beta": info.get("beta"),
    "forward_pe": info.get("forwardPE"),
    "price_to_book": info.get("priceToBook"),
    "roe": info.get("returnOnEquity"),
    "debt_to_equity": info.get("debtToEquity"),
    "earnings_growth": info.get("earningsGrowth"),
    "revenue_growth": info.get("revenueGrowth"),
    "news": news_items,  # list of {title, publisher, link, published_at}
}
```

### `GET /ticker/{symbol}` (`app/api/routes.py`)
- Return `profile` key from `stock_data` document directly (already stored by the live comparison run).
- If `profile` is absent (never run), lazy-hydrate from yfinance and `$set` to DB.

### MongoDB `stock_data` collection
- `profile` sub-document added — additive, no migration needed.

---

## Frontend Changes (`TickerModal.jsx`)

### New tab — Profile (placed **last** after Smart Rolls, or always visible after Price Action)
- Icon: `Building2` from lucide-react
- Tab accent color: `text-teal-400`

### `ProfileView` Component Layout
```
┌──────────────────────────────────────────────────────────────────┐
│  [Yahoo Finance News ↗]                          [Website ↗]     │
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │ Sector     │ │ Industry   │ │ Style/Type │ │ Exchange   │   │
│  │ Technology │ │ Semis      │ │ EQUITY     │ │ NMS        │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ Beta    1.63 │ Fwd P/E 35.2 │ P/B    38.1  │ ROE   119%  │  │
│  │ D/E    0.41  │ EPS Gr 88%   │ Rev Gr 122%  │ #Ana   42   │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                  │
│  Analyst: [STRONG BUY ▲]  42 opinions                           │
│                                                                  │
│  Description:                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ NVIDIA Corporation designs and manufactures...  [Show more]│ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Recent News                                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ ● [NVDA surges after earnings beat] — Reuters · 2h ago     │ │
│  │ ● [AI chip demand accelerates...]   — Bloomberg · 1d ago   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Style
- Dark theme, data-dense (Juicy Fruit standard)
- Analyst recommendation color-coded: `strong_buy`/`buy` → green, `hold` → yellow, `sell`/`strong_sell` → red
- Description `line-clamp-3` with Show more toggle
- News items as clickable rows, newest first

---

## Links
- [Implementation Plan](../plans/implementation_plan-20260328-stock_analysis_profile_tab.md)
- [features-requirements.md L141](../features-requirements.md)
