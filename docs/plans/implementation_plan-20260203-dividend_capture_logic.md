# Implementation Plan - Dividend Capture Analysis

## Goal Description
Implement the "Analysis" phase of the Dividend Capture features. When a user selects a ticker from the Dividend Feed, the system should analyze and propose specific **Buy-Write (Covered Call)** strategies that maximize the capture of the dividend while hedging against the post-dividend price drop.

## User Review Required
> [!NOTE]
> **Strategy Logic**: I will propose 3 variations of the Buy-Write strategy for each opportunity:
> 1.  **Protective (ITM)**: High probability of exercise. Income comes from Dividend + Time Value. High downside protection.
> 2.  **Balanced (ATM)**: Captures highest time value (premium). Good balance of risk/reward.
> 3.  **Aggressive (OTM)**: Captures Dividend + Stock Appreciation. Highest risk if stock drops more than dividend.

## Proposed Changes

### Backend (`app/`)

#### [MODIFY] [dividend_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/dividend_scanner.py)
- Import `RollService` to leverage `get_option_chain_data`.
- Add method `analyze_capture_strategy(ticker_symbol)`:
    - Helper: Find Ex-Dividend Date.
    - Helper: Find first Expiration Date > Ex-Dividend Date.
    - Helper: Fetch Option Chain (Calls) for that expiry.
    - Logic: Select 3 Strikes (One slightly ITM, One ATM, One slightly OTM).
    - Logic: Calculate Metrics for each:
        - **Net Cost**: `Stock Price - Premium Received`
        - **Max Profit**: `(Strike - Net Cost) + Dividend` (if assigned) or `(Price - Net Cost) + Dividend`?
            - *Simplification*: Assume held through Ex-Date. 
            - **Max Return**: `(Dividends + Premium + (Strike - CurrentPrice))/CurrentPrice` (if called).
        - **Breakeven**: `Current Price - Premium - Dividend`.
        - **Downside Protection**: `%` drop allowed before loss.

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- Add GET `/api/analysis/dividend-capture/{ticker}` endpoint.
    - Calls `DividendScanner.analyze_capture_strategy`.

### Frontend (`frontend/src/`)

#### [MODIFY] [DividendAnalysisModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/DividendAnalysisModal.jsx)
- Fetch analysis data on mount (`useEffect` depending on `opportunity.symbol`).
- Render a "Strategy Selection" list instead of just static text.
- For each strategy (Protective, Balanced, Aggressive), show:
    - **Strike** & **Expiry**
    - **Premium**
    - **Net Entry Cost**
    - **Max Return** & **Yield**
    - **Breakeven**
- Add "Execute" button (Log only for now).

## Verification Plan

### Automated Tests
- **New Test**: `tests/test_dividend_capture_analysis.py`
    - Mock `yfinance` option chain.
    - Verify selection of ITM/ATM/OTM strikes.
    - Verify calculation of "Max Return" and "Breakeven".

### Manual Verification
- Click a ticker in Dividend Feed.
- Verify Modal opens and loads strategies.
- Check math on one strategy (e.g., Net Cost = Price - Premium).
