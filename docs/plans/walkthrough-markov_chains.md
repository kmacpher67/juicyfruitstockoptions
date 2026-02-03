# Walkthrough - Markov Chains & Kalman Filters Signals

## Overview
Implemented a new **Signal Generation Service** that leverages **Kalman Filters** and **Markov Chains** to provide advanced technical analysis and probabilistic outlooks for portfolio tickers.

## Changes Made

### 1. New Service: `SignalService`
**File**: [`app/services/signal_service.py`](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/signal_service.py)

-   **Kalman Filter**: Implemented a 1D Kalman Filter to smooth price data.
    -   *Logic*: Generates a "True Price" estimate. If Current Price > Estimate, it triggers an "Above Trend" signal.
-   **Markov Chain**: Implemented a state-transition model.
    -   *Logic*: Discretizes daily returns into states (UP, FLAT, DOWN) and calculates the probability of future moves based on historical patterns.
-   **Advice Engine**: `get_roll_vs_hold_advice` uses these probabilities to suggest whether to Hold (if market is weak/reverting) or Roll (if strong momentum is detected) for Short Calls.

### 2. API Endpoint
**File**: [`app/api/routes.py`](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)

-   **Endpoint**: `GET /api/analysis/signals/{ticker}`.
-   **Response**:
    ```json
    {
      "ticker": "SPY",
      "kalman": {
        "signal": "Above Trend ...",
        "current_price": 500.20,
        "kalman_mean": 498.50
      },
      "markov": {
        "current_state": "UP_SMALL",
        "transitions": { ... }
      }
    }
    ```

### 3. Verification
-   **Unit Tests**: Created `tests/test_signal_service.py` verifying core logic with mock data.
-   **Integration Tests**: Created `tests/test_api_signals.py` ensuring the API correctly instantiates the service and mocks external calls (`yfinance`).

## Validation Results
-   All new tests passed.
-   Prototype script (`prototypes/markov_kalman_test.py`) validated the mathematical correctness of the implementations.

## Next Steps
-   Integrate these signals into the **Frontend** (Ticker Modal).
-   Use the "Roll vs Hold" advice in the **Smart Roll** assistant.
