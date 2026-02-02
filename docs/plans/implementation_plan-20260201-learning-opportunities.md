# Implementation Plan - Learning Opportunities & Research

**Goal**: Address all "Learning Opportunity" items identified in `docs/features-requirements.md`. This involves creating educational documentation, researching technical decisions (Agent frameworks, Backtesting engines), and documenting business logic (Opportunity scoring, Trade metrics).

## User Review Required
> [!NOTE]
> This plan focuses on **Documentation and Research**. No code changes are planned for this phase, but the outcome will likely drive future feature requirements.

## Proposed Changes

We will create a new directory `docs/learning/` to house these educational documents.

### Documentation & Learning Architecture
#### [NEW] [trade-metrics.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/trade-metrics.md)
*   **Goal**: Explain "Win Rate", "Profit Factor", and other metrics currently used or planned for Trade History.
*   **Content**:
    *   Formulas for Win Rate (Win / Total) and Profit Factor (Gross Win / Gross Loss).
    *   Explanation of "Diagonal Roll" impact (realized loss vs unrealized gain).
    *   Handling of Dividends in metrics.
    *   Recommendations for best practices.

#### [NEW] [opportunity-scoring.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/opportunity-scoring.md)
*   **Goal**: Define the "Rating value score rubric" for the Opportunity Finder.
*   **Content**:
    *   Current scoring logic (if any).
    *   Proposed robust scoring rubric (0-100 scale).
    *   Factors: IV Rank, Delta, Theta/Decay, Technical Trend (MA).
    *   Testing strategy for this logic.

#### [NEW] [juicy-thresholds.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/juicy-thresholds.md)
*   **Goal**: Define quantitative thresholds for "Juicy" trades.
*   **Content**:
    *   IV Rank thresholds (e.g., >50).
    *   Delta ranges (0.30 - 0.40 for OTM calls).
    *   Liquidity requirements (Open Interest, Volume).
    

#### [NEW] [kalman-filters.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/kalman-filters.md)
*   **Goal**: Explain the relevance of Kalman Filters in trading.
*   **Content**:
    *   Concept: Signal vs Noise separation.
    *   Use cases: Mean Reversion (pairs trading), Trend extraction.
    *   References/Papers usage in HFT/Algo trading.

#### [NEW] [backtesting-engines.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/backtesting-engines.md)
*   **Goal**: Compare Event-Driven vs Vectorized backtesting engines.
*   **Content**:
    *   **Vectorized** (VectorBT): Fast, good for initial research, harder to model complex order types.
    *   **Event-Driven** (Zipline/Backtrader): Slower, realistic (slippage, liquidity), handles complex logic.
    *   Recommendation for Juicy Fruit (likely Event-Driven for options).

#### [NEW] [agent-frameworks.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/agent-frameworks.md)
*   **Goal**: Discuss building Agents: LangChain/Frameworks vs Specialized Libraries.
*   **Content**:
    *   **LangChain/LangGraph**: General purpose, good for "Chat with Data" and orchestration.
    *   **Lumibot/Specialized**: Built for execution, risk management, connection to brokers.
    *   Hybrid approach recommendation.

#### [NEW] [bad-trade-heuristics.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/bad-trade-heuristics.md)
*   **Goal**: Define "Bad Trade" patterns to warn against.
*   **Content**:
    *   0DTE risks (Gamma risk).
    *   Earnings gambles (IV Crush).
    *   Low liquidity (wide spreads).
    *   Chasing losses (revenge trading).

### Plan Updates
#### [MODIFY] [features-requirements.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/features-requirements.md)
*   Update the "Learning Opportunity" items to point to these new documents.
*   Promote any solidified requirements (e.g., "Implement exclusion logic for Diagonal Rolls") to active Todo items.

## Verification Plan
### Manual Verification
*   **Review**: User to review the generated markdown files for clarity and accuracy.
*   **Links**: Verify all links in `features-requirements.md` correctly point to the new learning docs.
