# Kalman Filters in Trading

## What is a Kalman Filter?
In simple terms, a Kalman Filter is an optimal estimation algorithm that infers parameters of interest from indirect, inaccurate, and uncertain observations. It is recursive, meaning it updates its estimate as each new data point arrives.

## Why use it in Trading?
Financial time series are notoriously noisy. Moving Averages (SMA/EMA) are the traditional way to "smooth" data, but they suffer from **lag**.

*   **Lag Reduction**: Kalman Filters can adapt to changing market conditions faster than comparable moving averages.
*   **Dynamic Response**: It separates the "Signal" (True Price Trend) from the "Noise" (Random Market Fluctuation).

## Use Cases for Juicy Fruit

### 1. Mean Reversion (Pairs Trading)
The most common application. When trading a pair of assets (e.g., KO vs PEP), the relationship (hedge ratio) is not constant; it evolves over time.
*   **Kalman Application**: precise estimation of the dynamic hedge ratio (beta) between two assets.
*   **Strategy**: When the spread deviates significantly from the Kalman-predicted value, take a position expecting reversion.

### 2. Trend Following
*   Using a Kalman Filter to estimate the "Slope" of the price.
*   If Slope > 0 + Threshold -> Buy.
*   If Slope < 0 - Threshold -> Sell.

### 3. Hedging
*   Dynamically adjusting the delta of a portfolio. Instead of using a static Black-Scholes delta (which assumes constant volatility), a Kalman Filter can estimate the "Effective Delta" based on recent price behavior.

## Implementation Libraries
*   **Python**: `pykalman`, `filterpy`.
    *   `pykalman` is older but standard.
    *   `filterpy` (by Roger Labbe) is excellent for learning and has a great companion book ("Kalman and Bayesian Filters in Python").

## Reference Strategy
> *Statistical Arbitrage: Pairs Trading with Kalman Filter*
> This approach treats the spread between two cointegrated stocks as a hidden state to be estimated. It allows the model to "learn" if the relationship is breaking down or just wide due to noise.
