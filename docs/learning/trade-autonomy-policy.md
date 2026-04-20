# Trade Autonomy Policy

**Current Level: 0 — Zero Trust**  
**Owner:** Ken MacPherson  
**Updated:** 2026-04-19

---

## Principle

> "The system is a decision support tool, not a decision maker. Ken executes all trades."

Juicy Fruit has no write access to IBKR TWS API (no order submission permissions exist in the codebase today). All trades are advisory: the system surfaces opportunities, scores them, and formats parameters — Ken reviews and manually submits via IBKR desktop or mobile.

---

## Current Level: 0 — Zero Trust

**What the system does:**
- Identifies opportunities and scores them
- Surfaces roll candidates, x-div plays, covered call targets
- Calculates strike, premium, DTE, yield — formats them for review
- Does NOT submit orders, modify positions, or trigger any IBKR API write calls

**What Ken does:**
- Reviews all recommendations on the Juicy Fruit dashboard
- Decides which trades to execute
- Copy/pastes parameters into IBKR TWS or mobile
- Confirms fills, tracks outcomes manually for now

**Why Level 0:** Ken recognizes the risk of over-automation causing mistakes — specifically the trap of getting consumed by analysis and forgetting to act (e.g., rolling positions that went ITM). Paradoxically, the first automation candidates are the oversight failures, not the alpha-seeking decisions.

---

## Path to Semi-Automation (Future)

### Level 1 — Order Ticket Generation (Near-term, safe)
System generates pre-filled order parameters that Ken can review and submit with minimal effort.  
**No code change required** — this is a UI improvement (structured order summary in the modal/drawer).

**Candidates:**
- "Roll this covered call" → formats exact order: BTC current + STO new strike/expiry + net credit
- "BTC at 50% profit" → formats BTC limit order for the position

**Risk:** Zero. Ken still submits everything.

### Level 2 — Supervised Automation (Medium-term, requires sandbox)
System submits specific predefined low-risk order types with a mandatory human review window.

**Prerequisites:**
- IBKR paper trading account sandbox fully operational
- All rules proven with ≥30 days of paper-trade parity first
- Hard guardrails: position size limits, max loss limits, no market orders ever
- "Emergency stop" accessible from the dashboard
- Every submitted order logged with full reasoning trail

**First candidates for Level 2:**
1. **BTC at 50% profit** — buy to close a short option when market price = 50% of premium collected. Low risk, disciplined exit rule, easily audited.
2. **Expiration day BTC sweep** — close any position with DTE=0 and value < $0.05 to avoid accidental assignment risk.

### Level 3 — Limited Rule-Based Automation (Long-term, requires extensive validation)
Specific scenario-based auto-execution within tightly bounded rules.

**Example scenarios Ken identified as automation candidates:**
- **Roll expired/ITM covered calls:** When a covered call expires ITM on Friday night, auto-roll to a new contract (BTC + STO) with pre-defined roll parameters. This is where Ken made the costly Friday mistake.
- **Defensive BTC trigger:** If underlying drops X% intraday, auto-close put to avoid assignment.

**Prerequisites for Level 3:**
- Level 2 sandbox parity proven with ≥90 days of data
- Each rule independently backtested against graded history
- Ken explicitly approves each rule's definition before activation
- Maximum capital at risk per rule is hard-coded (not configurable from UI)
- Two-factor confirmation before enabling any Level 3 rule
- Monthly review of all automation outcomes by Ken

### Level 4 — Full Automation
**Not planned.** Too many edge cases, tax implications, and judgment calls that require Ken's discretion. Strategy requires discretionary human overlay.

---

## Safety Guardrails (All Levels)

These apply regardless of automation level:

| Guardrail | Rule |
|---|---|
| Position limits | No automation may create a new position exceeding X% NAV (TBD by Ken) |
| Market orders | Never. Limit orders only. |
| Earnings proximity | No automated trades within 3 days before / 1 day after earnings |
| Assignment risk | No automated selling of puts/calls within 5 DTE without explicit override |
| ITM options | No automated action on deep ITM options (Δ > 0.80) |
| Emergency stop | Single-click halt accessible from any dashboard page |
| Audit log | Every automated action persisted to `automation_audit_log` collection forever |
| Tax events | Flag any automation that creates a short-term taxable event in IRA vs taxable accounts |

---

## The Friday Problem (Motivation for Controlled Automation)

> "I forgot to roll some taxable trades and got caught ITM. These might be worth automating first, if we can sandbox and safety."

The specific failure pattern:
1. Friday expiration approaches with covered call ITM
2. Ken is occupied / distracted
3. No roll executed before close
4. Assigned over the weekend — creates unexpected stock sale, potential taxable event

**Proposed Level 2/3 automation for this:** Friday DTE sweep — if any short call/put has DTE=1 and is ITM, generate an alert (Level 1) or optionally submit a BTC before 3pm ET (Level 2, with 30-min confirmation window).

**Key constraint:** Taxable vs IRA accounts must be treated separately. An ITM covered call assignment in a taxable account has different P&L and tax implications vs IRA.

---

## Metrics for Evaluating Automation Quality

Before activating any automation level, these metrics must be proven in paper trading:

| Metric | Threshold |
|---|---|
| Hit rate (paper) | ≥ 65% WIN outcomes for the specific automation rule |
| Yield delta | Automated exits must achieve ≥ 90% of optimal exit yield vs manual |
| False positive rate | < 10% of automation triggers should have been overridden by Ken |
| Slippage | Average fill vs limit price < $0.05 per contract |

---

## Current Status Checklist

- [x] TWS API write permissions: **NOT implemented** (intentional — Level 0)
- [ ] Paper trading account: needs verification/setup
- [ ] Order ticket UI (Level 1): not yet implemented
- [ ] BTC 50% profit rule: not yet implemented
- [ ] Friday DTE sweep alert: partially in ExpirationScanner — needs UI surface
- [ ] Automation audit log collection: not yet defined

---

*See also: [Juicy Glossary](juicy-glossary.md), [Smart Roll & Diagonal](smart-roll-diagonal.md), [Opportunity Scoring](opportunity-scoring.md)*
