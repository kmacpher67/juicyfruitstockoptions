# Implementation Plan - Juicy Opportunity Finder & Heuristics

This plan addresses the "Analysis & Signals" requirements, specifically the "Juicy Opportunity Finder" and "Bad Trade Heuristics" to help Trader Ken avoid bad trades and find good opportunities.

## Goal Description
Implement the "Bad Trade Heuristics" (RSI, ATR, Impatience checks) as a backend service and integrate these warnings into the Frontend `TickerModal`. Additionally, add "Smart Roll" suggestions to the Optimizer tab by leveraging the existing `RollService`.

## User Review Required
> [!IMPORTANT]
> **Data Dependency**: Calculating RSI and ATR requires historical data. `StockLiveComparison` currently fetches 1y history. We will calculate these indicators during the nightly/manual sync. Real-time RSI might deviate slightly from the stored value if the market moves significantly during the day, as `StockLiveComparison` runs periodically.
My trades data has a full year of data. 
What data do you need for analysis beyond the yf data?

## Proposed Changes

### Backend Components

#### [MODIFY] [stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py)
- **Add Indicators**:
    - `calculate_rsi(series, period=14)`: Relative Strength Index.
    - `calculate_atr(high, low, close, period=14)`: Average True Range.
- **Update Record**: Store `RSI` and `ATR` and `Distance_From_20SMA` in the record.

#### [NEW] [app/services/risk_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/risk_service.py)
- **Purpose**: Evaluate a ticker against "Ken's Bad Trades" heuristics.
- **Functions**:
    - `analyze_risk(ticker_data: dict) -> List[RiskWarning]`: 
        - Check **Impatience**: RSI > 75 (Long Call warning).
        - Check **Trend Extension**: Price > 20SMA + 3*ATR.
        - Check **Liquidity**: Spread > 10% of mid logic (if real-time data available or stored).
        - Check **Earnings**: If "Expected Earnings" is near (need to check if we can get this easily from `info`, otherwise skip for V1).

#### [MODIFY] [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **Update `/opportunity/{symbol}`**:
    - Call `RiskService.analyze_risk(data)` and include `risks` in the response.
- **Update `/portfolio/optimizer/{symbol}`**:
    - If the user has an existing position (check `ibkr_holdings`), use `RollService` to suggest specific rolls.
    - If no position, keep generic suggestions.

### Frontend Components

#### [MODIFY] [frontend/src/components/TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx)
- **Update `OpportunityView`**:
    - Display "Risk Warnings" section (Red Alerts) if any heuristics are triggered.
    - Show `RSI` and `ATR` in the Metrics grid.
- **Update `OptimizerView`**:
    - If "Rolls" are returned by backend, display them in a table (Expiration, Strike, Net Credit).

## Verification Plan

### Automated Tests
- **Backend Unit Tests**:
    - `tests/test_risk_service.py`:
        - Test Logic: Pass in mock data with RSI=80, expect "Impatience" warning.
        - Test Logic: Pass in mock data with Price >> SMA + 3*ATR, expect "Trend Extension" warning.
    - `tests/test_stock_indicators.py`:
        - Verify `calculate_rsi` against known values (simple array).
    - `tests/test_analysis_routes.py`:
        - Verify new response structure for `/opportunity/{symbol}`.

### Manual Verification
- **Run Live Comparison**:
    - Execute `run_stock_live_comparison_endpoint` (or script) to populate DB with new indicators.
- **Check Frontend**:
    - Open `TickerModal` for a high-flying stock (e.g., NVDA or a meme stock if available).
    - Verify "RSI" is displayed.
    - Verify if "Risk Warnings" appear (maybe artificially lower threshold to test).
