# Implementation Plan - Portfolio Management Features

## Goal Description
Implement "Portfolio Management" features as defined in `docs/features-requirements.md` (Epic 2, Portfolio Management).
Key goals:
1.  **Portfolio History Visualization**: Add an interactive time-series chart for NAV performance to the Dashboard.
2.  **Ticker Analytics**: Create a comprehensive Modal view for individual tickers showing Analytics, Opportunity, and Organization data.
3.  **Trade History Time Window**: Add time-based filtering (MTD, 1M, YTD, etc.) to the Trade History view.

## User Review Required
> [!IMPORTANT]
> **New API Routes**: Adding `/api/ticker/{symbol}`, `/api/opportunity/{symbol}`, and `/api/portfolio/optimizer/{symbol}` to `app/api/routes.py`.
> **Frontend Dependency**: Please confirm if `recharts` is already installed. If not, I will install it. checking `package.json`... (I will assume I need to check or install).

## Proposed Changes

### Backend

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
-   Add `GET /api/ticker/{symbol}`: Returns recent stats, current price, and basic info.
-   Add `GET /api/opportunity/{symbol}`: Returns "Juicy" scores, gap analysis, and trend info.
-   Add `GET /api/portfolio/optimizer/{symbol}`: Returns optimization suggestions (e.g., covered call candidates).
-   *Note*: These endpoints will reuse existing logic from `options_analysis.py`, `scanner_service.py`, and `option_optimizer.py`.

#### [MODIFY] [trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/trades.py)
-   Update `get_trade_analysis` to accept `start_date` and `end_date` parameters.
-   Implement filtering logic in the MongoDB query.

### Frontend

#### [NEW] [TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx)
-   Create a modal component with tabs: "Analytics", "Opportunity", "Optimizer".
-   Fetch data from the new API endpoints.

#### [MODIFY] [Dashboard.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/Dashboard.jsx)
-   Add `Recharts` LineChart to the "My Portfolio" view (below NAV Stats).
-   Integrate `TickerModal` and handle state for opening/closing.
-   Pass `onTickerClick` to `PortfolioGrid` (and `StockGrid` if applicable).

#### [MODIFY] [PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/PortfolioGrid.jsx)
-   Make the Ticker column clickable.
-   Trigger `onTickerClick`.

#### [MODIFY] [TradeHistory.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TradeHistory.jsx)
-   Add "Time Range" selector (All, MTD, 1M, 3M, 6M, YTD, 1Y).
-   Update API call to include date filtering.

### Tests

#### [NEW] [test_portfolio_features.py](file:///home/kenmac/personal/juicyfruitstockoptions/tests/test_portfolio_features.py)
-   Test `GET /api/ticker/{symbol}`.
-   Test `GET /api/opportunity/{symbol}`.
-   Test `GET /api/portfolio/optimizer/{symbol}`.

#### [MODIFY] [test_api_trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/tests/test_api_trades.py)
-   Add tests for date filtering in `get_trade_analysis`.

## Verification Plan

### Automated Tests
-   Run `pytest tests/test_portfolio_features.py` to verify new endpoints.
-   Run `pytest tests/test_api_trades.py` to verify trade filtering.

### Manual Verification
1.  **Portfolio Graph**: Open Dashboard -> My Portfolio. Verify the graph appears and shows history (if data exists).
2.  **Ticker Modal**: Click a ticker in the Portfolio Grid. Verify the modal opens and tabs work.
3.  **Trade History**: Go to Trade History. Change the Time Range filter. Verify the table updates.
