# Opportunity Scoring Rubric

To separate "noise" from "signal," the Opportunity Finder uses a quantitative scoring rubric (0-100) to rate potential "Juicy Fruit" trades.

## Scoring Factors

### 1. Implied Volatility (IV) Rank (Weight: 40%)
Options are expensive when IV is high. We want to sell premium when it is expensive.
*   **Metric**: `IV Rank` (current IV relative to the past 12 months).
*   **Score**:
    *   `> 75`: **100 points** (Juicy!)
    *   `50 - 75`: **80 points**
    *   `30 - 50`: **50 points**
    *   `< 30`: **0 points** (Premium is cheap, consider buying instead of selling).

### 2. Technical Trend (Weight: 30%)
We prefer writing Covered Calls on stocks that are stable or slightly bullish (neutral-bullish), or writing Puts on stocks that are oversold but fundamentally strong.
*   **Metric**: Price vs 50-day SMA and RSI.
*   **Score (for Covered Calls)**:
    *   `Price > 50 SMA` AND `RSI < 70`: **100 points** (Uptrend but not overbought).
    *   `Price > 50 SMA` AND `RSI > 70`: **50 points** (Uptrend but risk of pullback).
    *   `Price < 50 SMA`: **20 points** (Downtrend, careful catching a falling knife).

### 3. Liquidity (Weight: 20%)
We need to be able to enter and exit easily without losing edge to slippage.
*   **Metric**: Open Interest (OI) and Volume of the specific contract.
*   **Score**:
    *   `OI > 1000` & `Vol > 500`: **100 points**.
    *   `OI > 500`: **70 points**.
    *   `OI < 100`: **0 points** (Danger zone).

### 4. Yield / Return (Weight: 10%)
Does the premium justify the capital tied up?
*   **Metric**: `Annualized Return if Flat` (ARIF).
*   **Score**:
    *   `> 30%` annualized: **100 points**.
    *   `15% - 30%`: **70 points**.
    *   `< 10%`: **20 points**.

## Total Score Calculation
`Total Score = (IV_Score * 0.4) + (Trend_Score * 0.3) + (Liquidity_Score * 0.2) + (Yield_Score * 0.1)`

### Interpretation
*   **90 - 100**: **Juicy!** (Strong Sell signal).
*   **70 - 89**: **Good** (Consider if portfolio needs exposure).
*   **< 70**: **Pass** (Better opportunities exist).

## Testing Strategy
1.  **Backtesting**: Run this scoring algorithm against historical data. Did high-scoring trades outperform low-scoring trades?
2.  **Paper Trading**: Forward test signals in a paper account to verify "real-world" fillability and performance.

---

## Win/Loss Outcome Score (Grading Scale)

After a trade closes, it receives an **Outcome Score** separate from the opportunity score above.  
This measures realized performance against Ken's capital cost floor. See [Juicy Glossary](juicy-glossary.md).

### Ken's Inflation Baseline (~5.9%)
The zero point for real returns. Composite of PCE, CPI, IBKR margin rate (~6%), and US fiscal deficit/GDP (~5.8%).  
Any yield at or below this rate means capital did not beat its own cost.

### Outcome Score Anchors

| Score | Meaning | Annualized Yield |
|---|---|---|
| +100 | WIN — Juicy | ≥ 33% |
| +50 | Good | ≈ 20% |
| +10 | Beat inflation (barely) | ≈ 5.9% (Ken's Inflation Baseline) |
| 0 | Pure breakeven | 0% |
| -50 | Significant loss | ≈ -10% |
| -100 | LOSS — Capital destruction | ≤ -20% |

**Positive scale (0 → +100):** Linear interpolation from 0% yield (score 0) to 33%+ (score 100).  
Values between 0 and 10 are "nominally positive but below inflation" — not a real win.

**Negative scale (0 → -100):** Linear interpolation from 0% yield (score 0) to -20%+ loss (score -100).

### Outcome Classification
- **WIN**: Score ≥ 10 AND yield exceeds Ken's Inflation Baseline AND meets minimum position size threshold (TBD)
- **LOSS**: Score < 0 (any real money loss, annualized)
- **SCRATCH**: Score 0–9 (below inflation, not worth the capital tie-up)

### Grading Metrics Tracked (All Windows)
Per-ticker AND portfolio aggregate:

| Metric | Windows |
|---|---|
| Hit Rate (WIN%) | QTD, YTD, 1Y, All-time |
| Realized Annualized Yield | QTD, YTD, 1Y, All-time |
| Yield Delta (predicted vs actual) | Per trade + aggregate |
| Return (absolute $) | QTD, YTD, 1Y, All-time |
