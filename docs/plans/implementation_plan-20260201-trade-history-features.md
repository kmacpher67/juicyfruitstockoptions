# Implementation Plan - Trade History & Metrics

**Goal**: Enable users to view their entire trade history with calculated metrics (Cost Basis, Realized P&L) and summary statistics. This moves beyond simple data storage to actionable insights.

## User Review Required
> [!NOTE]
> This feature introduces meaningful P&L calculations. The "Matching Logic" (FIFO) will be the default.
> **Security**: New API endpoints will be protected by the existing `get_current_active_user` dependency.

## 1. Settings Updates
- No new env vars required.
- Existing MongoDB connection is sufficient.

## 2. ACL Security Roles Compliance
- Endpoints will require `role="analyst"` or higher (default basic users can view their own data, but for now we assume single-tenant/admin use or consistent RBAC).
- **Endpoint**: `/api/trades` -> Requires Auth.

## 3. Data Model ETL and Views
- **No Schema Change**: `ibkr_trades` remains the source of truth.
- **On-the-fly Analysis**: We will compute "Analyzed Trades" (P&L) in memory for the requested period.
- **New Models**:
    - `AnalyzedTrade`: Extends `TradeRecord` with `realized_pl`, `cost_basis`.
    - `TradeMetrics`: `total_pl`, `win_rate`, `profit_factor`.

## 4. New Routes or Service/Models
- **Service**: `app/services/trade_analysis.py`
    - logic for FIFO matching of Buy/Sell orders.
    - logic for metric aggregation.
- **Route**: `app/api/trades.py`
    - `GET /`: List trades (paginated).
    - `GET /analysis`: Return analyzed data + metrics.

## 5. Impact on AI Learning
- Code will be modular (`services/`) and typed, aiding future agents.

## 6. Compliance with Mission
- Directly supports "Analysis & Signals" and "Trader Ken's" goal of analyzing past performance.

## 7. Global Rules
- Code will follow strict typing, PEP8, and logging standards.

## 8. Best Practices
- **Separation of Concerns**: Ingestion (already done) vs Analysis (this plan).
- **Testing**: Heavy unit testing on the math (P&L calculation).

## 9. Epic Fit
- Completes "Get entire history of trades" in `docs/features-requirements.md`.

## 10. Document.md Rules
- Feature doc will be created: `docs/features/trade_history_analysis.md`.

## Proposed Changes

### Backend
#### [NEW] [app/services/trade_analysis.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/trade_analysis.py)
- `calculate_pnl(trades: List[TradeRecord]) -> List[AnalyzedTrade]`
- `calculate_metrics(trades: List[AnalyzedTrade]) -> TradeMetrics`

#### [NEW] [app/api/trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/trades.py)
- fastapi Router implementation.

#### [MODIFY] [app/models.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models.py)
- Add `AnalyzedTrade` and `TradeMetrics` models.

#### [MODIFY] [app/main.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/main.py)
- Include `trades` router.

### Frontend
#### [NEW] [app/frontend/components/TradeHistory.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/app/frontend/components/TradeHistory.jsx)
- Data Grid showing history.
- Summary Cards for `TradeMetrics`.

## Verification Plan

### Automated Tests (`pytest`)
- **Unit**: Test `calculate_pnl` with known scenarios (Buy 10 @ 100, Sell 5 @ 110 -> $50 P&L).
- **Integration**: Test API endpoint returns 200 OK and expected JSON structure.

### Manual Verification
- Browse to `/trades` in the UI.
- Verify numbers make sense against a known broker statement.
