# Opportunity Persistence & Grading (The "Truth" Engine)

## Overview
To scientifically improve trading performance, we must close the loop between **Signal Generation** (finding a "Juicy Opportunity") and **Outcome Realization** (what actually happened). 

Without persistence and grading, we cannot answer simple questions like:
- "Do our Gap Up signals actually make money?"
- "Is our High IV Rank threshold too aggressive?"

## The Lifecycle of a Signal

### 1. Detection (Signal Generation)
When the system identifies a potential trade (e.g., a Covered Call candidate), it is currently ephemeral—it appears on the dashboard and disappears when conditions change.
**Requirement**: We must **Snapshot** the opportunity.

**Data to Persist (`JuicyOpportunity` Schema):**
- **Trigger**: What logic flagged this? (e.g., `DividendScanner`, `GapScanner`).
- **Context**: 
    - Underlying Price at Trigger Time.
    - Implied Volatility (IV) Rank.
    - Greeks (Delta, Gamma, Theta) of the specific contract.
    - Bid/Ask Spread (Liquidity snapshot).
- **Proposal**: The specific trade (e.g., "Sell XYZ $100 Call exp 2026-03-20").
- **Timestamp**: Exact ISO timestamp of detection.

### 2. Validation ("Paper Trade")
Before a user even executes it, the system can treat every signal as a "Paper Trade".
- **Status**: `DETECTED` -> `TRACKING`.
- **Allocation**: Assume a standard position size (e.g., 1 lot or $1000 risk) for standardized comparison.

### 3. Tracking (Path Dependency)
A trade isn't just Start vs End. We need to know what happened *during* the life of the trade.
- **Max Favorable Excursion (MFE)**: How much profit did it show at its peak?
- **Max Adverse Excursion (MAE)**: How much drawdown did it endure?
- **Stop Loss Breach**: Did it hit a theoretical stop loss?

### 4. Grading (Outcome)
At expiration or a predefined exit criteria (e.g., 50% profit), the opportunity is closed and graded.
- **Result**: `WIN` / `LOSS`.
- **PnL**: Normalized profit/loss.
- **Efficiency**: ROI / Days Held.

## Feedback Loop (Calibration)
Once we have a database of 100+ graded opportunities, we can run **Signal Correlation Analysis**:
- "Signals with IV Rank > 70 have a 50% higher win rate than those with IV Rank < 30."
- "Gap Fill signals on Mondays tend to fail."

This data allows us to tune the **Opportunity Scorer** weights based on empirical reality, not just intuition.
