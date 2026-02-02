# Implementation Plan - Smart Roll & Dividend UI

## Goal
Implement the user interface for the recently added backend features: Smart Roll Assistant, Dividend Capture Scanner, and Dividend Calendar Export.
The goal is to surface these insights directly in the `PortfolioGrid` and `TickerModal` to assist decision making.

## User Review Required
> [!NOTE]
> **Design Pattern**: We will use a new "Smart Roll" tab in the `TickerModal` for detailed position analysis, and a "Scanner" dashboard (or modal) for the Dividend Capture list.

## Proposed Changes

### Frontend

#### [MODIFY] [PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/PortfolioGrid.jsx)
- **Add Button**: "Export Dividend Calendar" (Header).
    - Action: `window.open('/api/calendar/dividends.ics', '_blank')`.
- **Add Button**: "Scan Smart Rolls" (Header).
    - Action: Open a summary modal or navigate to a view showing `roll_service.analyze_portfolio_rolls` results.
    - *Alternative*: Display a "Smart Roll Available" badge on rows that have high-scoring rolls?

#### [MODIFY] [TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx)
- **Add Tab**: "Smart Rolls" (Visible only if position is held).
- **Content**:
    - Fetch rolls for this specific ticker (Backend API update might be needed if we want *single* ticker rolls? Or just filter the portfolio list?).
    - *Decision*: For now, we call the backend `RollService.find_rolls` for this ticker? No, `analyze_portfolio_rolls` is for the whole portfolio.
    - **New Query**: We likely need a `GET /api/analysis/rolls/{symbol}` endpoint or reuse the service logic for on-demand analysis in the modal.
    - **Display**: Table of rolls (Strike, Exp, Credit, Score). Highlight "Dividend Risk".

#### [NEW] [components/DividendScanner.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/DividendScanner.jsx)
- **Purpose**: Display results from `/api/analysis/dividend-capture`.
- **UI**: Table showing Ticker, Ex-Date, Yield, Est. Dividend, and "Buy-Write" Score.
- **Integration**: Add to `Dashboard.jsx` or as a standalone route/modal.

#### [MODIFY] [Dashboard.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/Dashboard.jsx)
- Import and render `DividendScanner` (perhaps in a new "Opportunities" section).

### Backend (Supporting Changes)

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **New Endpoint**: `GET /api/analysis/rolls/{symbol}`.
    - Allows the `TickerModal` to fetch smart rolls for *just* the current symbol on demand, without re-scanning the whole portfolio.

## Verification Plan

### Manual Verification
1.  **Calendar**: Click "Export Dividend Calendar" in Portfolio. Verify `.ics` download and content.
2.  **Dividend Capture**: Open Dashboard. Verify "Dividend Opportunities" list populates (Mock data if needed or real data).
3.  **Smart Rolling**:
    - Click a stock in Portfolio.
    - Open "Smart Rolls" tab.
    - Verify list of rolls appears with Scores.
    - Check "Dividend Risk" warning logic (if applicable).

### Automated Tests
- **Frontend Tests**: (If React testing setup exists) - currently we rely on manual UI verification for this project structure.
- **Backend Tests**: Verify the new `GET /api/analysis/rolls/{symbol}` endpoint works.
