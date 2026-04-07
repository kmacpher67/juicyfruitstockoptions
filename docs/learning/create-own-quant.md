You are a quant trader and developer. You are building a stock analysis tool for yourself. 

## How to Build Your Own Quant Alpha Lab

### 1. Idea Generation & Hypothesis
* **Describe a market inefficiency to Claude** (e.g., "crypto opening range breakout").
* **Formulate a clear hypothesis** for an alpha signal.
* **Claude suggests statistical tests** and relevant market variables to explore.
* **Outputs a structured research proposal** with defined entry and exit criteria.

### 2. Data & Feature Engineering
* **Request Claude to write code** for a robust data pipeline from multiple sources (tick, order book, alternative data).
* **Create custom features:** ask Claude for indicators like z-scores, volatility regimes, and cross-asset correlations.
* **Handle data cleaning, normalization, and feature scaling** automatically.

### 3. Backtesting & Validation
* **Claude writes backtesting logic** with realistic assumptions (slippage, fees).
* **Perform in-sample testing and crucial out-of-sample (walk-forward) analysis** to prove signal robustness.
* **Calculate key metrics:** Sharpe ratio, Sortino ratio, max drawdown, and win rate.

### 4. Optimization & Stress Testing
* **Use Claude to design and run a parameter optimization matrix** to find stable regions, not single best points.
* **Implement Monte Carlo simulations** to test strategy performance under thousands of "worst-case" scenarios.
* **Detect over-fitting and "p-hacking"** by analyzing the distribution of backtest results.

### 5. Generate Research Report
* **Compile all findings** into a comprehensive, automated research report.
* **Includes equity curves, performance metrics, parameter stability heatmaps**, and a final "Go/No-Go" verdict for deployment.
* **A self-contained, interactive HTML or PDF document** for peer review.

---

### Tips
* **Simplicity:** Start with simple hypotheses. Complex models often overfit.
* **Data Purity:** Ensure your backtest data is free from survivor bias and look-ahead bias.
* **Iterate:** Research is non-linear. Expect to loop back to hypothesis generation often.
* **Extend:** Explore machine learning models (e.g., random forests) for signal combination after validating simple alpha.