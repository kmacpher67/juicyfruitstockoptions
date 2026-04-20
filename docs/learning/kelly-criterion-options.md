# Kelly Criterion for Options Traders

**Author Reference:** Edward Thorp (popularized for financial markets)  
**Application:** Position sizing in Juicy Fruit Thorp Audit tab (`stock-analysis-thorpe-004`)  
**Related:** [Thorp Protocol Investing](thorp-protocol-investing.md)

---

## Core Formula

```
f* = (b × p - q) / b
```

Where:
- `f*` = fraction of capital to deploy (Kelly optimal bet size)
- `b` = net odds (what you win per $1 risked)
- `p` = probability of winning
- `q = 1 - p` = probability of losing

**Thorp's practical rule:** Always use **Half-Kelly** (`f*/2`) in live trading. Real probabilities are estimated, not known — half-Kelly captures ~75% of theoretical growth while dramatically reducing ruin risk.

---

## Applying Kelly to Options Strategies

### Covered Call (Wheel — Sell Call)

```
b = premium_received / (cost_basis - premium_received)
p = probability_OTM  (from delta: p ≈ 1 - |delta|)
q = 1 - p
```

**Example:**
- AMD @ $150, sell $160 call for $3.50 premium
- Cost basis: $150
- `b = 3.50 / (150 - 3.50) = 3.50 / 146.50 ≈ 0.0239`
- Delta of $160 call: 0.25 → `p ≈ 0.75`, `q = 0.25`
- `f* = (0.0239 × 0.75 - 0.25) / 0.0239 = (0.01793 - 0.25) / 0.0239`
- `f* = -9.7` → **negative Kelly = do not take this trade as sized**

This illustrates why Kelly works: a trade with small premium relative to risk shows a negative Kelly. The correct interpretation is the premium is too small for the assignment risk — go further OTM or skip.

### Cash-Secured Put (Wheel — Sell Put)

```
b = premium_received / (strike - premium_received)
p = probability_OTM  (p ≈ 1 - |delta| for puts)
```

**Example:**
- AMD @ $150, sell $140 put for $4.00 premium
- `b = 4.00 / (140 - 4.00) = 4.00 / 136 ≈ 0.0294`
- Put delta = -0.20 → `p ≈ 0.80`, `q = 0.20`
- `f* = (0.0294 × 0.80 - 0.20) / 0.0294 = (0.0235 - 0.20) / 0.0294`
- `f* = -6.0` → **negative Kelly** — standard result for single-leg options

**Why are options Kelly values typically negative?**  
Single-leg naked premium yields appear attractive but the asymmetric risk (premium vs full assignment cost) produces negative Kelly when evaluated as a pure bet. The correct framing is portfolio Kelly: the entire portfolio has a positive Kelly if covered calls are layered on a long equity position with positive expected return.

### Portfolio Kelly for Covered Calls

The correct way to apply Kelly to a covered call position:

```
f* = (E[return] - r) / σ²
```

Where:
- `E[return]` = expected annualized return of (long equity + covered call premium)
- `r` = risk-free rate
- `σ²` = variance of the combined position return

This is the **continuous Kelly** (Breiman/Kelly for log-normal assets). For implementation in `thorp_service.py`, use:

```python
# Simplified portfolio Kelly estimate
expected_return = (annualized_yield_pct / 100) + equity_drift
risk_free = system_config.get("risk_free_rate", 0.053)  # current 3-mo T-bill
variance = (realized_vol ** 2)
kelly_fraction = (expected_return - risk_free) / variance
half_kelly = kelly_fraction / 2
```

---

## Half-Kelly Safety Margins

| Fraction | Expected Growth Rate | Ruin Probability |
|---|---|---|
| Full Kelly (f*) | Maximum long-run growth | ~50% over time if estimates wrong |
| Half Kelly (f*/2) | ~75% of max growth | Low — highly recommended |
| Quarter Kelly (f*/4) | ~56% of max growth | Near zero |

**Thorp's recommendation:** Half-Kelly in all real-world applications. Full Kelly assumes perfect knowledge of probabilities — which no trader has.

---

## Position Sizing in `thorp_service.py`

```python
def compute_kelly_position_size(
    annualized_yield_pct: float,     # from juicy_opportunities
    win_rate: float,                  # from trades history
    avg_loss_pct: float,              # from trades history
    current_nlv: float,               # from ibkr_holdings
    current_position_value: float,    # from ibkr_holdings
) -> dict:
    # Approximate b: yield per unit risk
    b = annualized_yield_pct / 100 / max(avg_loss_pct / 100, 0.01)
    p = win_rate
    q = 1 - win_rate
    if b <= 0:
        return {"status": "INSUFFICIENT_DATA", "kelly": None}
    f_star = (b * p - q) / b
    half_kelly = max(f_star / 2, 0)
    recommended_pct = half_kelly * 100
    current_pct = (current_position_value / current_nlv) * 100 if current_nlv > 0 else 0
    if current_pct > recommended_pct * 1.25:
        status = "CAUTION"  # over-committed by >25%
    elif current_pct < recommended_pct * 0.5:
        status = "EDGE"     # significant room to add
    else:
        status = "EDGE"
    return {
        "status": status,
        "kelly_full": round(f_star * 100, 2),
        "kelly_half": round(half_kelly * 100, 2),
        "current_exposure_pct": round(current_pct, 2),
        "recommended_pct": round(recommended_pct, 2),
    }
```

---

## Common Mistakes

1. **Applying single-bet Kelly to options**: Options have asymmetric payoff structures — use portfolio Kelly, not single-bet Kelly.
2. **Using full Kelly**: Over-betting with estimation error leads to ruin. Always half-Kelly.
3. **Ignoring correlation**: If multiple positions in the same sector, effective Kelly fraction is lower — diversification is built into the denominator of portfolio Kelly.
4. **Over-sizing small-premium trades**: A 2% yield on a 90-DTE covered call over a $150 stock is a tiny `b` — Kelly will tell you to size very small or not at all relative to a higher-yielding candidate.

---

## References
- Kelly, J.L. (1956). "A New Interpretation of Information Rate." *Bell System Technical Journal.*
- Thorp, E. (1997). "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market." *10th International Conference on Gambling and Risk Taking.*
- MacLean, L.C., Thorp, E.O., Ziemba, W.T. (2011). *The Kelly Capital Growth Investment Criterion.* World Scientific.
