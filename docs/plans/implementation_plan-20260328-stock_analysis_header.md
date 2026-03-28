# Stock Analysis Header Update

**Date:** 2026-03-28  
**Feature Ref:** `features-requirements.md` L137  
**Status:** Planning  

## Problem

The TickerModal popup header currently displays: **TICKER $XX.XX ±X.XX%**  
The requirement is to show: **TICKER | Company Name | $XX.XX | ±X.XX% | Date/Time of last update**  
Plus: link TICKER → Google Finance, link Company Name → Yahoo Finance.

## Proposed Changes

### Backend — Stock Data Pipeline

#### [MODIFY] [stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py)

Add `Company Name` field to the record built in `fetch_ticker_record()` (line ~299):

```diff
 record = {
     "Ticker": ticker,
+    "Company Name": info.get("longName") or info.get("shortName") or ticker,
     "Current Price": current_price,
```

This stores the company name from yfinance's `info` dict alongside existing data. Per user rule about storing more data than immediately needed, we capture both `longName` (preferred) and fall back to `shortName`.

---

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)

Enrich the `/ticker/{symbol}` response (line ~1090) to provide `company_name` even if it's missing from MongoDB (for legacy records that were stored before this field existed):

```diff
 @router.get("/ticker/{symbol}")
 @log_endpoint
 def get_ticker_analysis(
     symbol: str,
     current_user: Annotated[User, Depends(get_current_active_user)]
 ):
     symbol = symbol.upper().strip()
     client = MongoClient(settings.MONGO_URI)
     db = client.get_default_database("stock_analysis")
     
     stock = db.stock_data.find_one({"Ticker": symbol}, {"_id": 0})
     if not stock:
         return {"symbol": symbol, "found": False, "price": 0.0}
-        
-    return {"symbol": symbol, "found": True, "data": stock}
+    
+    # Provide company_name at top level for header convenience
+    company_name = stock.get("Company Name")
+    if not company_name:
+        try:
+            import yfinance as yf
+            info = yf.Ticker(symbol).info
+            company_name = info.get("longName") or info.get("shortName") or symbol
+            # Backfill to DB for future requests
+            db.stock_data.update_one(
+                {"Ticker": symbol},
+                {"$set": {"Company Name": company_name}}
+            )
+        except Exception:
+            company_name = symbol
+    
+    return {"symbol": symbol, "found": True, "data": stock, "company_name": company_name}
```

---

### Frontend — TickerModal Header

#### [MODIFY] [TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx)

Update header section (lines 58-75) to:
1. Link TICKER → `https://www.google.com/finance/quote/{TICKER}` (opens new tab)
2. Show company description linked → `https://finance.yahoo.com/quote/{TICKER}/` (opens new tab)
3. Show Last Update timestamp from `tickerData.data['Last Update']`

```jsx
{/* Header */}
<div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
    <div className="flex items-baseline gap-3 flex-wrap">
        <a href={`https://www.google.com/finance/quote/${ticker}`}
           target="_blank" rel="noopener noreferrer"
           className="text-3xl font-bold text-blue-400 hover:text-blue-300 hover:underline transition-colors">
            {ticker}
        </a>
        {tickerData?.company_name && tickerData.company_name !== ticker && (
            <a href={`https://finance.yahoo.com/quote/${ticker}/`}
               target="_blank" rel="noopener noreferrer"
               className="text-sm text-gray-400 hover:text-yellow-400 hover:underline transition-colors">
                {tickerData.company_name}
            </a>
        )}
        {tickerData?.data ? (
            <>
                <span className="text-xl font-mono text-blue-400">
                    ${tickerData.data['Current Price']}
                </span>
                <span className={`text-sm ${tickerData.data['1D % Change'] >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {tickerData.data['1D % Change']}%
                </span>
                {tickerData.data['Last Update'] && (
                    <span className="text-xs text-gray-500" title="Last data update">
                        {tickerData.data['Last Update']}
                    </span>
                )}
            </>
        ) : (
            <span className="text-sm text-gray-500">Loading price...</span>
        )}
    </div>
    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
        <X className="w-6 h-6" />
    </button>
</div>
```

---

## Checklist (per create-a-plan workflow)

| # | Item | Status |
|:--|:-----|:-------|
| 1 | Settings — No new env vars needed | ✅ |
| 2 | ACL — No new roles/permissions | ✅ |
| 3 | Data Model — Adds `Company Name` field to existing `stock_data` collection. No migration needed; backfills on-demand | ✅ |
| 4 | Routes — Modifies existing `/ticker/{symbol}`, no new routes | ✅ |
| 6 | Mission compliance — Enhances dashboard per user request | ✅ |
| 7 | Gemini.md rules — Follows type-hinting, logging, test standards | ✅ |
| 8 | Industry best — Progressive enhancement, graceful fallback | ✅ |
| 9 | Features-requirements — Updates L137 status | ✅ |
| 10 | Documentation — Feature doc to be created | ⏳ |
| 12 | Testing — See Verification Plan below | ⏳ |

## Verification Plan

### Automated Tests

1. **Existing test update** — Modify `test_fetch_ticker_record` in `tests/test_stock_live_methods.py` to assert `Company Name` is present in the record:
   ```bash
   pytest tests/test_stock_live_methods.py::test_fetch_ticker_record -v
   ```

2. **New unit test** — Add `test_fetch_ticker_record_company_name` to verify `Company Name` uses `longName` → `shortName` → ticker fallback chain.

3. **Existing test sanity** — Run full test suite to verify no regressions:
   ```bash
   pytest tests/test_stock_live_methods.py -v
   ```

### Browser Verification

- Open the app, click a ticker in StockGrid → verify TickerModal header shows:
  - Ticker as clickable link → opens Google Finance in new tab
  - Company name as clickable link → opens Yahoo Finance in new tab
  - Price + % change + Last Update timestamp

### Manual Verification

- Verify the Google Finance URL format: `https://www.google.com/finance/quote/{TICKER}`
- Verify the Yahoo Finance URL format: `https://finance.yahoo.com/quote/{TICKER}/`

## Changelog

| Date | Action | Reason |
|:-----|:-------|:-------|
| 2026-03-28 | **CREATED** | Initial plan for Stock Analysis Header enhancement |
