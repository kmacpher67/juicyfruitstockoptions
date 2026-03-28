# Implementation Plan — Stock Analysis Profile Tab
**Date**: 2026-03-28
**Feature**: Add Profile sub-tab to TickerModal with yfinance profile + news data
**Feature Doc**: [docs/features/stock_analysis_profile_tab.md](../features/stock_analysis_profile_tab.md)
**PRD Line**: [features-requirements.md L141](../features-requirements.md)

---

## Checklist Review

### 1. Settings Updates
- [x] No new env vars needed. yfinance already in use.
- [x] No config changes.
- [x] Impact: `stock_data` collection gains a `profile` sub-document. Additive — backward compatible.

### 2. ACL Security Roles
- [x] No new roles. Profile uses same `get_current_active_user` as `/ticker/{symbol}`.

### 3. Data Model / ETL
- [x] `stock_data` collection: `profile` sub-document added during live comparison run.
- [x] Lazy hydration on first `/ticker/{symbol}` call if `profile` absent.
- [x] No migration needed — additive change.

### 4. New Routes / Services / Models
- [x] No new route — extends existing `/ticker/{symbol}`.

### 6. Refresh Cadence
**Two triggers — both already exist, just need to write to `profile`:**
- **Manual**: "Run Live Comparison" button → `POST /run/stock-live-comparison` → `run_stock_live_comparison()` → `StockLiveComparison.fetch_ticker_record()` → `upsert_to_mongo()`
- **Scheduled**: APScheduler runs `run_stock_live_comparison` daily at `system_config.hour:minute`
- **Fallback**: `/ticker/{symbol}` lazy-hydrates if `profile` field is absent from DB record

---

## Implementation Steps

### Step 1 — `stock_live_comparison.py`: Add `profile` to `fetch_ticker_record()`

In `fetch_ticker_record(self, ticker, info, hist, chain)`, add a `profile` sub-document to the returned record.
`info` is already fetched. `chain` is the yfinance `Ticker` object — use it to fetch `.news`.

```python
# Fetch recent news (up to 5 items)
try:
    raw_news = chain.news or []
    news_items = [
        {
            "title": n.get("title", ""),
            "publisher": n.get("publisher", ""),
            "link": n.get("link", ""),
            "published_at": datetime.fromtimestamp(n["providerPublishTime"]).strftime("%Y-%m-%d %H:%M")
            if n.get("providerPublishTime") else "",
        }
        for n in raw_news[:5]
    ]
except Exception:
    news_items = []

profile = {
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
    "news": news_items,
}
record["profile"] = profile
```

Add this block just before `return record`.

### Step 2 — `app/api/routes.py`: Return `profile` from `/ticker/{symbol}`

Existing logic fetches the `stock` document from `stock_data`. Extend to:
1. Check if `stock.get("profile")` exists.
2. If absent (record pre-dates this feature), lazy-hydrate from yfinance and `$set` to DB.
3. Include `profile` in return payload.

```python
profile = stock.get("profile")
if not profile:
    try:
        info = yf.Ticker(symbol).info
        raw_news = yf.Ticker(symbol).news or []
        profile = {
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
            "news": [
                {
                    "title": n.get("title", ""),
                    "publisher": n.get("publisher", ""),
                    "link": n.get("link", ""),
                    "published_at": datetime.fromtimestamp(n["providerPublishTime"]).strftime("%Y-%m-%d %H:%M")
                    if n.get("providerPublishTime") else "",
                }
                for n in raw_news[:5]
            ],
        }
        db.stock_data.update_one({"Ticker": symbol}, {"$set": {"profile": profile}})
        logging.info(f"routes.get_ticker_analysis - Lazy-hydrated profile for {symbol}")
    except Exception as e:
        logging.warning(f"routes.get_ticker_analysis - Could not fetch profile for {symbol}: {e}")
        profile = {}

return {"symbol": symbol, "found": True, "data": stock, "company_name": company_name, "profile": profile}
```

### Step 3 — `TickerModal.jsx`: Add Profile tab

1. Import `Building2` from `lucide-react`.
2. Add tab button after Price Action (always shown, not conditional like Smart Rolls).
3. Add `{activeTab === 'profile' && <ProfileView data={tickerData} ticker={ticker} />}` to content.

### Step 4 — `TickerModal.jsx`: Implement `ProfileView` component

Full component with:
- Quick links row (Yahoo Finance News + Website)
- Profile grid (Sector, Industry, Style, Exchange, Country, Employees)
- Fundamentals grid (Beta, Forward P/E, P/B, ROE, D/E, Earnings Growth, Revenue Growth, Analyst count)
- Analyst recommendation badge (color-coded)
- Description with line-clamp-3 + Show more toggle
- Recent news list (title linked to article, publisher, time ago)

### Step 5 — Backend Tests

File: `tests/test_routes_ticker_profile.py`
- Test `/ticker/{symbol}` returns `profile` key when record has it in DB.
- Test lazy hydration path writes to DB (mock yfinance, assert `update_one` called).
- Test graceful fallback: yfinance raises, `profile` returned as `{}`.

---

## Definition of Done
- [ ] `fetch_ticker_record` writes `profile` sub-document on every live comparison run
- [ ] `/ticker/{symbol}` returns `profile` key (from DB or lazy-hydrated)
- [ ] Profile tab visible and functional in TickerModal
- [ ] Description truncate/expand works
- [ ] Yahoo Finance News link visible and correct
- [ ] Analyst recommendation badge color-coded
- [ ] News headlines render with links
- [ ] All new tests pass (`pytest tests/test_routes_ticker_profile.py`)
- [ ] `features-requirements.md` L141 marked `[x]`
- [ ] Feature doc updated
