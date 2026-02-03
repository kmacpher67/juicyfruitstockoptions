# Implementation Plan - Dividend Feed UI

## Goal Description
Implement the **Dividend Feed UI** as specified in `features-requirements.md`. This involves enhancing the list of dividend opportunities to include detailed holding info (Accounts & Qty), predicted pricing, and specific sortable columns.

## User Review Required
> [!NOTE]
> **Predicted Price Logic**: Per user request, we will upgrade the prediction logic to use a **Hybrid Model**:
> 1. **Markov Chain Simulation**: We will extend `SignalService` to simulate price movement up to the Ex-Date based on historical transition probabilities.
> 2. **Analyst Targets**: We will fetch `targetMeanPrice` from `yfinance` as a long-term anchor.
> 3. **The Prediction**: The "Predicted Price" will be the result of the Markov Simulation (short-term accuracy), while displaying the Analyst Target as context (long-term sentiment).

## Proposed Changes

### Backend (`app/`)

#### [MODIFY] [signal_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/signal_service.py)
- Implement `predict_future_price(ticker, days_ahead, current_price)`:
    - Build/Retrieve Markov Transition Matrix.
    - Run Monte Carlo simulation (e.g., 100 paths) for `days_ahead`.
    - Return `mean_predicted_price` and `confidence_interval`.

#### [MODIFY] [dividend_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/dividend_scanner.py)
- Inject `SignalService`.
- In `scan_dividend_capture_opportunities`:
    - Fetch Analyst Target (`ticker.info.get('targetMeanPrice')`).
    - Call `SignalService.predict_future_price(symbol, days_to_ex, current_price)`.
    - Adjust prediction for dividend drop if crossing ex-date (technically prediction is "at open on ex-date", so it should reflect drop?). -> *Decision: Predict Pre-Open price, then subtract dividend for "Ex-Open" price.*
    - Aggregate: Date, Ticker, Account/Qty, Current Price, **Markov Predicted Price**, **Analyst Target**, Dividend, Yield.

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- Update `scan_dividend_capture` endpoint to return this enhanced data structure.

### Frontend (`frontend/src/`)

#### [MODIFY] [DividendListModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/DividendListModal.jsx)
- Update the Grid/Table to display the new columns.
- Implement client-side sorting (or ensure backend sorting if paginated, but list is likely small enough for client sorting).
- Columns:
    - **Date** (Ex-Div Date)
    - **Ticker**  There should be only one Ticker per row, so this column should be sortable.
    - **Accounts & Qty** Aggregate the accounts and qty for each Ticker. 
    - **Current Price**
    - **Predicted Price** (Markov Sim @ Ex-Date)
    - **Analyst Target** (1Y Mean)
    - **Div Amount**
    - **Return**
    - **Yield** (%)
    - **Days to Div**

## Verification Plan

### Automated Tests
- `pytest tests/test_dividend_scanner_feed.py` (New test for detailed feed data structure)
- Verify `Accounts & Qty` aggregation logic.

### Manual Verification
- Open Dividend Widget/Modal.
- Verify all columns appear.
- Test sorting by clicking headers.
- Verify data matches known holdings (from Portfolio page).
