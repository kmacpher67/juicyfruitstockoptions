# Juicy Fruit Glossary — Trading Strategy Terms & Definitions

Master reference for Juicy Fruit strategy terms, scoring concepts, and economic baselines.  
All definitions are Ken MacPherson's specific interpretations, not textbook or IBKR defaults.

---

## Core Performance Benchmarks

### Ken's Inflation Baseline
**The zero point. The cost of doing nothing.**

A composite rate representing the true cost of capital and money — not the Federal Reserve's politically adjusted CPI figure.

**Components (equal-weight average):**

| Component | Current Value | Source |
|---|---|---|
| Mean Average PCE (Personal Consumption Expenditures) | ~3.5–4% | BEA / Fed |
| CPI (Consumer Price Index) | ~3–3.5% | BLS |
| IBKR Margin Interest (cost of Ken's actual capital) | ~6–6.5% | IBKR account |
| US Federal Fiscal Deficit / GDP | ~5.7–5.8% | $1.78T deficit / ~$31T GDP (FY2025) |

**Composite: ~5.8–5.9%**

> Why NOT the Fed's 2.7%? The Fed's CPI excludes volatile food/energy and is structurally distorted by decades of near-zero rates and fiscal expansion. Real cost of money = what it costs Ken to borrow (margin) + what the government is printing relative to economic output. Fed numbers are useful for policy but misleading for personal capital allocation.

**Significance:** Any trade returning less than Ken's Inflation Baseline is a real-money loss even if nominally profitable. Score 0 is this threshold — you broke even against cost of capital, but you didn't make money.

---

### WIN Definition
**Annualized Yield significantly above Ken's Inflation Baseline.**

> WIN = Annualized Yield > 33% for a meaningful position size and time frame.

- **Score 100**: Annualized yield ≥ 33%
- **Score 10–99**: Annualized yield linearly interpolated between Ken's Inflation Baseline (~5.9%) and 33%
- **Score 10**: Annualized yield ≈ Ken's Inflation Baseline (~5.9%) — you beat inflation but barely
- **Score 1–9**: Annualized yield between 0% and Ken's Inflation Baseline — nominally positive but lost to inflation

**Anchors:**
```
Score 100  → Yield ≥ 33%     (Juicy Win — exceptional premium capture)
Score  50  → Yield ≈ 20%     (Good — exceeds any reasonable cost of capital)
Score  10  → Yield ≈ 5.9%    (Ken's Inflation Baseline — breakeven after capital cost)
Score   0  → Yield = 0%      (Pure breakeven — no profit, no loss)
```

**Significance threshold:** A WIN must also exceed a minimum dollar amount (TBD — needs Ken's definition, e.g., $100 net premium or $500 position size) to filter out technically-high-yield micro-positions that aren't worth the operational overhead.

---

### LOSS Definition
**Annualized Yield below zero — actual money lost.**

> LOSS = Annualized Yield < 0% (time value of money is negative)

- **Score 0**: Yield = 0% (pure breakeven)
- **Score -1 to -99**: Annualized loss linearly interpolated from 0% to 20%
- **Score -100**: Annualized loss ≥ 20%

**Anchors:**
```
Score    0  → Yield = 0%       (Breakeven — no profit, no loss)
Score  -50  → Yield ≈ -10%    (Significant loss)
Score -100  → Yield ≤ -20%    (Major loss — capital destruction)
```

---

### Full Score Scale Summary

```
+100  ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ≥33% annualized yield (WIN)
 +50  ●━━━━━━━━━━━━━━━━━━━━━━━━           ≈20% yield (Good)
 +10  ●━━━━━━━                             ≈5.9% yield (Ken's Inflation — not a real win)
   0  ●                                    0% yield (Pure breakeven)
 -50  ●━━━━━━━━━━━━━━━━━━━━━━━━           ≈-10% annualized loss
-100  ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ≤-20% annualized loss (LOSS)
```

> **Important:** Score is always based on **annualized yield** normalized by position size — not raw dollar P&L. A $5 premium on a $10,000 position annualized to 30 DTE is scored the same as a $500 premium on a $100,000 position annualized to 30 DTE.

---

## Trade Outcome Terms

### DTE (Days to Expiration)
Calendar days until option contract expiration. DTE = 0 means expiration day.  
See also: [DTE Calculation Standards](dte-calculation-standards.md)

### Expired Worthless
Short option expires with zero intrinsic value. The full premium collected at open is realized profit.  
Outcome: `WIN` if annualized yield meets threshold. Classification: `EXPIRED_WORTHLESS`.

### Assignment
Counterparty exercises the option. Ken is obligated to buy (put) or sell (call) the underlying at strike.  
May be a WIN or LOSS depending on cost basis, strike, and premium collected.  
Classification: `ASSIGNED`.

### Roll
Close current option position and open a new one with different strike/expiry, typically for a net credit.  
Outcome deferred until new position resolves. Classification: `ROLLED`. See [Smart Roll & Diagonal](smart-roll-diagonal.md).

### BTC (Buy to Close)
Buying back a short option position before expiration. Exits the trade.  
Profit = premium collected at open − cost to close.

### Annualized Yield
The most important normalization metric for comparing trades of different duration:
```
Annualized Yield = (Net Premium / Capital at Risk) × (365 / DTE) × 100
```
Where Capital at Risk = strike price × 100 (for options) or stock position cost basis.

### MFE (Max Favorable Excursion)
The maximum profit the trade showed at any point during its life before closing.  
Used to detect "left money on the table" and optimize early-exit rules.

### MAE (Max Adverse Excursion)
The maximum loss the trade showed at any point during its life before closing.  
Used to calibrate stop-loss rules and assignment risk.

---

## Strategy Terms

### Covered Call
Selling a call option against 100 shares of stock owned. Caps upside but generates premium income.  
Covered = STK qty == abs(short_call_qty × 100)

### Wheel Strategy
Sell cash-secured puts → if assigned, sell covered calls → repeat.  
Generates income in sideways/mild bull markets.

### Diagonal Spread
Buy a longer-dated option + sell a shorter-dated option at a different strike.  
Reduces cost basis of the long while capping gains. See [Smart Roll & Diagonal](smart-roll-diagonal.md).

### Juicy Fruit (Trade)
A covered call or short put with a score ≥ 70 on the Juicy scoring rubric. See [Opportunity Scoring](opportunity-scoring.md).

### X-DIV (Ex-Dividend Date)
The date on which a stock must be held to receive the next dividend. Option assignment before x-div can trigger early exercise risk for short calls.  
See [X-DIV Rolling Strategy](x-div-rolling.md).

---

## Metrics & Aggregation Definitions

### Hit Rate
Percentage of graded trades that result in WIN outcome:
```
Hit Rate = WIN count / Total Graded count × 100%
```

### Yield Delta (Predicted vs Actual)
Difference between the predicted annualized yield (at scoring time) and the realized annualized yield (at outcome):
```
Yield Delta = Realized Yield − Predicted Yield
```
Positive = outperformed prediction. Negative = underperformed.

### Aggregate Metrics Tracked
Per-ticker AND portfolio aggregate, across all standard time windows:

| Metric | Description |
|---|---|
| **Hit Rate** | WIN% for the period |
| **Annualized Yield (realized)** | Average yield of closed trades |
| **Yield Delta** | Predicted vs actual, per trade and aggregated |
| **Return** | Absolute $ P&L |
| **YTD** | Year-to-date aggregate |
| **QTD** | Quarter-to-date aggregate |
| **1Y** | Rolling 12-month |

---

## Trade Automation Autonomy Levels

See [Trade Autonomy Policy](trade-autonomy-policy.md) for full definition and roadmap.

| Level | Name | Description |
|---|---|---|
| **0** | Zero Trust (Current) | Ken manually executes all trades. System is advisory only. Copy/paste into IBKR. |
| **1** | Semi-Supervised | System generates order ticket parameters. Ken reviews, approves, submits. |
| **2** | Supervised Automation | System submits predefined low-risk orders (e.g., BTC at 50% profit) with human override window |
| **3** | Limited Automation | Specific rule-based automation (e.g., roll expired options) with hard guardrails |
| **4** | Full Automation | Not planned. Requires extensive production validation first |

**Current Status: Level 0 — Zero Trust**

---

*Last updated: 2026-04-19 | Owner: Ken MacPherson*
