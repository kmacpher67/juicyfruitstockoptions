# Markov Chains & Kalman Filters for Signal Generation

## 1. Introduction
This document explores the use of **Markov Chains** and **Kalman Filters** for generating trading signals, specifically focusing on trend following, mean reversion, and the "Roll vs. Hold" decision-making process for options.

## 2. Kalman Filters
The Kalman Filter is a mathematical algorithm that uses a series of measurements observed over time (containing statistical noise) to produce estimates of potential unknown variables.

### Application in Trading
-   **Trend Following**: By estimating the "true" state (price or trend) from noisy market data, Kalman Filters can smooth out price action better than simple moving averages (SMA/EMA) because they dynamically adjust to volatility.
-   **Mean Reversion**: We can calculate the deviation of the current price from the Kalman-estimated "true" price. 
    -   *Signal*: If Price << Kalman Estimate -> Potential Oversold (Buy).
    -   *Signal*: If Price >> Kalman Estimate -> Potential Overbought (Sell).
-   **Pairs Trading**: Estimating the dynamic hedge ratio between two assets.

### Prototype Results
Using `pykalman`, we successfully smoothed 1 year of SPY data. The filter provided a dynamic "mean" line that reacted faster than traditional MAs but smoother than the raw price, allowing for clear "Above Trend" vs "Below Trend" signals.

## 3. Markov Chains
A Markov Chain is a stochastic model describing a sequence of possible events in which the probability of each event depends only on the state attained in the previous event.

### Application in Trading
-   **State Definition**: We define market states based on returns (e.g., `UP_BIG`, `UP_SMALL`, `FLAT`, `DOWN_SMALL`, `DOWN_BIG`).
-   **Transition Matrix**: We calculate the probability of moving from one state to another (e.g., P(UP | DOWN)).
-   **Signal Generation**: 
    -   If P(DOWN | UP_BIG) is high -> Reversal Signal.
    -   If P(UP | UP_SMALL) is high -> Momentum Signal.

### Roll vs. Hold Strategy
This is where Markov Chains shine for options management.
-   **The Problem**: Should I hold an option (hoping for favorable move) or roll it (extending time)?
-   **The Markov Approach**:
    1.  **Predict Future State**: Use the transition matrix to simulate future price paths for the underlying asset over the next $N$ days (until expiration).
    2.  **Expected Value (EV)**:
        -   *EV_Hold*: Simulation of holding current option to expiration.
        -   *EV_Roll*: Simulation of closing current and opening new position (factoring in roll credit/debit).
    3.  **Decision**: If EV_Roll > EV_Hold + Transaction Costs -> **ROLL**.

### Prototype Results
Using `markovify` (adapted for categorical data) and manual transition matrices, we successfully generated probabilistic paths for SPY. The transition matrix showed, for instance, a 48% chance of continuing up after a big up day (Momentum) vs a reversal chance.

## 4. Implementation Strategy

### Prerequisites
-   `pykalman`: For trend/mean reversion signals.
-   `markovify` or `pandas` (manual): For state transition matrices.
-   Historical Data: OHLCV data (already available via `yfinance`).

### Proposed Workflow
1.  **Signal Generation Service**: Create a background service that:
    -   Updates Kalman estimates daily for all portfolio tickers.
    -   Updates Markov Transition Matrices (re-trained weekly).
2.  **Portfolio Integration**:
    -   In `StockGrid` or `PortfolioGrid`, show "Trend Status" (from Kalman).
    -   In `SmartRoll` modal, add "Probabilistic Outlook" (from Markov simulation).

## 5. Pros & Cons

| Method | Pros | Cons |
| :--- | :--- | :--- |
| **Kalman Filter** | Adaptive, lags less than MAs, handles noise well. | Computationally heavier than MAs. Needs tuning (covariance matrices). |
| **Markov Chain** | Probabilistic (gives % chance), good for discrete regimes. | "Memoryless" assumption might miss long-term context. Needs discretized data. |

## 6. Next Steps
-   Implement `KalmanSignalService` in the backend.
-   Integrate into `OptionAnalyzer` for "Smart Roll" logic.
