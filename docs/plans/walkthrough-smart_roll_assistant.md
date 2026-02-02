# Walkthrough - Smart Roll Assistant

**Date**: 2026-02-02
**Feature**: Smart Roll / Diagonal Assistant
**Status**: Implemented

## Changes Overview

Implemented a sophisticated "Smart Roll" strategy that analyzes existing short call positions and suggests optimal rolling opportunities based on:
1.  **Greeks & Risk**: Gamma Risk (getting out of <7 DTE if Gamma high), Delta Preference (~0.30).
2.  **Momentum**: 1D % Change driving "Urgency" bonuses.
3.  **Financials**: Net Credit > 0 (Yield Bonus) and Strike Improvement.

### Key Components

#### 1. Greeks Calculation
Integrated `py_vollib_vectorized` via `GreeksCalculator` to enrich standard Yahoo Finance option chains with Delta, Gamma, and Theta.

#### 2. Scoring Logic (`RollService.score_roll`)
A weighted scoring algorithm (0-100) that prioritizes:
- **Credit (40%)**: Bonus for $>0.5\%$ yield.
- **Strike Improvement (30%)**: Bonus for moving from ITM to OTM.
- **Duration (20%)**: Preference for short duration (< 10 days) extension.
- **Momentum & Greeks**: Bonuses for escaping high Gamma risk or leveraging bullish momentum.

#### 3. API Endpoint
`GET /api/analysis/rolls`
- Scans the user's portfolio.
- Filters for Short Calls.
- Returns sorted suggestions with full context (Greeks, Score, Reason).

## Verification Results

### Automated Tests (`tests/test_smart_roll.py`)
| Test Case | Description | Result |
| --- | --- | --- |
| `test_score_roll_basic` | Verifies Credit, Yield, and Duration logic correctness. | ✅ PASSED |
| `test_score_roll_momentum` | Verifies bullish momentum adds urgency bonus. | ✅ PASSED |
| `test_score_roll_greeks` | Verifies Delta preference (0.30 target) and Gamma penalty avoidance. | ✅ PASSED |
| `test_analyze_portfolio_rolls` | Integration test for portfolio iteration and filtering. | ✅ PASSED |
| `test_get_smart_rolls_endpoint` | Verifies API connectivity and response structure. | ✅ PASSED |

### Manual Verification Steps
1.  Start backend: `uvicorn app.main:app --reload`
2.  Hit endpoint: `curl http://localhost:8000/api/analysis/rolls`
3.  Observe JSON output containing `score`, `delta`, `gamma` fields.

## Next Steps
- **UI Integration**: Build the "Smart Roll" widget in the Portfolio view to display these suggestions.
