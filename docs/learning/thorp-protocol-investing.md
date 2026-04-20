# Edward Thorp's 10-Point Investment Protocol

**Source:** Thorp's work across *Beat the Dealer*, *A Man for All Markets*, and interviews with Jack Schwager.  
**Application:** Juicy Fruit per-ticker decision audit in `TickerModal.jsx` → Thorp Audit tab.  
**Related:** [Kelly Criterion for Options](kelly-criterion-options.md)

---

## Core Principle

> "Assume you may have an edge only when you can make a rational affirmative case that withstands your attempts to tear it down." — Edward Thorp

Thorp never placed a bet without a *verified, mathematical edge*. The 10 points below are a structured protocol for applying this discipline to every options trade decision.

---

## The 10 Framework Points

### 1. Edge Audit
**Question:** Do I actually have a provable edge, or am I trading on hope?

**Juicy Fruit Implementation:**
- Compare ticker historical win rate from `trades` collection against the **inflation baseline** (default 5.9%, stored in `system_config.thorp_inflation_baseline`).
- Edge formula: `E = win_rate × avg_yield - (1 - win_rate) × avg_loss`
- Status: `EDGE` if `E > inflation_baseline`; `CAUTION` if `0 < E < baseline`; `RISK` if `E ≤ 0`.

### 2. Position Sizing — Kelly Criterion
**Question:** Am I over-committed (ruin risk) or under-committed (wasted edge)?

**Formula:** `f* = (b × p - q) / b`

Where: `b` = net odds (payout ratio), `p` = win probability, `q = 1 - p`

**Thorp's practical rule:** Use *half-Kelly* (`f*/2`) because real-world probabilities are estimates.

See: [Kelly Criterion for Options](kelly-criterion-options.md) for options-specific formula variants.

### 3. Inefficiency Map
**Question:** Where is the market mispricing this ticker?

**Signals to flag:**
- **Call/Put Skew > 1.5**: Market is pricing downside protection at a premium — potential edge selling puts.
- **IV vs RV gap > 20%**: Implied volatility exceeds realized — option premium is elevated (seller's edge).
- **Earnings premium collapse**: IV crush post-earnings creates short-term covered call opportunity.

### 4. Ruin Check — Black Monday Simulation
**Question:** If the stock drops 25% overnight, can I survive?

**Implementation:**
- Simulate `-25%` drop on current position market value from `ibkr_holdings`.
- Compute Net Liquidation impact in dollars and as % of total NLV.
- Status `RISK` if simulated loss > 10% of total NLV.
- Thorp's rule: *"If the answer is no, reduce your borrowing immediately."*

### 5. Fraud Scan (Mispricing Detector)
**Question:** Is anything here "too good to be true"?

**Checks:**
- Option volume > 3× average daily volume: unusual activity flag.
- Option premium > Black-Scholes theoretical value by > 30%: possible mispricing or data error.
- Liquidity grade `D`: spread cost dominates premium — execution quality too poor to trust stated yield.

### 6. Compounding Review
**Question:** Is this position compounding my capital, or consuming it linearly?

**Implementation:**
- Display `annualized_yield_pct` from `juicy_opportunities` alongside average days held from `trades`.
- Compare actual annualized return vs a flat linear growth model at the inflation baseline.
- Flag positions held > 180 days with < baseline annualized yield as "compounding drag."

### 7. Adaptability Check — Edge Decay
**Question:** Is my edge on this ticker/strategy dying?

**Implementation:**
- Pull last 3–4 trade outcomes for `(ticker, strategy)` combination from `trades`.
- Compute yield trend slope (linear regression over sequential trades).
- Status `CAUTION` if slope shows > 15% decline per cycle.
- Thorp: *"Every stock market system with an edge is necessarily limited. Edges get crowded and die."*

### 8. Independence Test — Crowded Consensus
**Question:** Am I following the crowd instead of thinking for myself?

**Implementation:**
- Compare `stock_data.news_sentiment` score against `stock_data.markov_prediction` signal direction.
- Flag as "crowded consensus" when both agree AND news sentiment is > 70% bullish/bearish.
- Thorp's Madoff lesson: consensus is not evidence. Crowded trades need larger margin of safety.

### 9. Circle of Competence
**Question:** Is this ticker/strategy in my proven skill set?

**Implementation:**
- Categorize ticker by `asset_class` (STK/OPT) and `strategy` (Covered Call / Wheel / Put Sell).
- Look up Trader Ken's historical win rate for this exact `(asset_class, strategy)` category from `trades`.
- Status `EDGE` if category win rate > 60%; `CAUTION` if 40-60%; `RISK` if < 40% or < 5 samples.

### 10. The Thorp Decision — Top 3 Moves
**Question:** Given all of the above, what are the 3 highest-expected-value actions right now?

**Implementation:**
- Aggregate status scores from points 1–9 (weighted: Ruin Check and Edge Audit weighted 2×).
- Generate ranked action list:
  1. **Increase** (Kelly says under-bet + Edge confirmed + no Ruin risk)
  2. **Roll / Adjust** (Inefficiency or Adaptability flags triggered)
  3. **Exit / Reduce** (Ruin risk or Circle of Competence failure)
- Each action includes: edge rationale, specific risk, and concrete first step.

---

## Implementation Notes for `thorp_service.py`

- Each point must return `status: INSUFFICIENT_DATA` if required fields are absent — never fabricate numbers.
- Points 3 (Inefficiency) and 7 (Adaptability) may return partial results if only some sub-checks have data.
- Cache computed audit in `stock_data.thorp_audit` with a 30-minute TTL to avoid redundant recompute on repeated modal opens.
- All logging must follow project standard: `{datetime} - {filename-class-method} - {LEVEL} - {message}`.

---

## References
- Thorp, E. (2017). *A Man for All Markets.* Random House.
- Thorp, E. (1962). *Beat the Dealer.* Vintage.
- Schwager, J. (2012). *Hedge Fund Market Wizards.* Wiley. (Thorp interview)
