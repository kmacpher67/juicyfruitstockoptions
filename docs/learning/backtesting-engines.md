# Backtesting Engines: Vectorized vs Event-Driven

When building a backtesting framework for options strategies ("Juicy Fruit"), the choice of engine is critical.

## 1. Vectorized (e.g., VectorBT)
Calculates all signals and returns for the entire history in one go (using Pandas/NumPy array operations).

*   **Pros**:
    *   **Speed**: Extremely fast. Can test thousands of parameter combinations in seconds.
    *   **Simplicity**: Great for simple "Buy and Hold" or "Slightly Complex" signals (e.g., SMA crossover).
*   **Cons**:
    *   **Look-ahead Bias**: Easy to accidentally use future data.
    *   **Complexity Limit**: Very hard to model complex path-dependent logic (e.g., "If I get assigned on my short put, then sell a call, but only if IV is high...").
    *   **Options**: Hard to model options expiration cycles and strike selection logic vectorized.

## 2. Event-Driven (e.g., Zipline, Backtrader, Lean)
Simulates the market bar-by-bar (or tick-by-tick). The code loops through time, and at each step, you only see data up to that moment.

*   **Pros**:
    *   **Realism**: Accurately handles slippage, commission, liquidity, and order types.
    *   **Path Dependency**: Perfect for "The Wheel" strategy where today's action depends on yesterday's trade result.
    *   **No Look-ahead Bias**: The architecture prevents it.
*   **Cons**:
    *   **Speed**: Much slower than vectorized.
    *   **Code**: More verbose.

## Recommendation for Juicy Fruit: **Event-Driven**
Since the core strategies involve **Options** and **Lifecycle Management** (Rolling, Assignment, Wheel), a Vectorized approach will likely fail to capture the nuance.

*   **Choices**:
    *   **Backtrader**: Popular, Pythonic, but development has slowed.
    *   **Lean (QuantConnect)**: Robust, C# core with Python wrapper, huge community, "Local" version available.
    *   **Zipline**: Used by Quantopian (RIP), powerful but finicky setup.
    *   **Custom**: Build a lightweight event loop specific to our needs. Given we are dealing with daily/hourly data (not HFT), a custom Python loop is often the best balance of control and simplicity.
