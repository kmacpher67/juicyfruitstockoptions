# Implementation Plan - Smart Roll / Diagonal Assistant

## Goal
Implement the "Smart Roll / Diagonal Assistant" to analyze existing short calls in the portfolio and suggest optimal rolling strategies (Calendar/Diagonal Spreads). The goal is to optimize for short duration, favorable return/yield, and risk management.

## User Review Required
> [!NOTE]
> This plan focuses on the **Backend Implementation** (Service logic + API). Frontend UI integration will be done in a subsequent task to keep changes atomic, unless requested otherwise.

## Proposed Changes

### Backend

#### [MODIFY] [roll_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/roll_service.py)
- **New Method**: `analyze_portfolio_rolls(portfolio_items, max_days_to_expiration=10)`
    - Iterates through portfolio items looking for Short Calls (`qty < 0`, `sec_type="OPT"`, `right="C"`).
    - Filters for options expiring within `max_days_to_expiration`.
    - Calls `find_rolls` for each candidate.
- **Enhance Method**: `find_rolls`
    - Logic update: Calculate "Roll Yield" and "Annualized Return".
    - Logic update: Implement `score_roll` logic based on:
        - **Credit**: Higher credit = Higher score.
        - **Strike Improvement**: Increasing strike width (if underlying > strike) = Higher score.
        - **Duration**: Shorter duration preferred (e.g., < 10 days).
        - **Momentum Logic**: Use `One_Day_Change` (1D %) to adjust scoring (e.g., Bullish + DTE 2 = Urgency Bonus).
    - **Note**: Advanced "Gamma/Theta" logic described in learning docs requires Greeks data, which is currently missing. This plan implements the Momentum/Duration logic first.
    - Return a sorted list of "Smart Rolls" with scores.
- **New Method**: `score_roll(roll_data, current_position_data, market_metrics)`: Helper to calculate the 0-100 score.

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **New Endpoint**: `GET /api/analysis/rolls`
    - Fetches current portfolio (using `IBKRService` or cached data).
    - Calls `RollService.analyze_portfolio_rolls`.
    - Returns list of roll opportunities grouped by ticker.

## Verification Plan

### Automated Tests
- **Run Unit Tests**: `pytest tests/test_roll_service.py`
    - **New Test**: `test_analyze_portfolio_rolls`: Mock a portfolio with short calls and verify it finds them and calls `find_rolls`.
    - **New Test**: `test_score_roll`: Verify scoring logic (e.g., ensuring a Net Credit roll scores higher than a Debit roll).
    - **Update Test**: `test_find_rolls`: Verify new metrics (Yield, Annualized Return) are present.

### Manual Verification
1.  **Start Backend**: `uvicorn app.main:app --reload`
2.  **Trigger Analysis**: Use `curl` or Swagger UI (`http://localhost:8000/docs`) to hit `GET /api/analysis/rolls`.
3.  **Inspect Output**: Verify JSON response contains roll suggestions for actual short calls (if any) or mocked data if using a test mode.
