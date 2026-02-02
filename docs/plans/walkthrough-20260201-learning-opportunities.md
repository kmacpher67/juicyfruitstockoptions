# Walkthrough - Learning Opportunities Completion

I have addressed all the "Learning Opportunity" items in `docs/features-requirements.md`. This involved researching the questions raised and creating educational documentation to serve as a reference for future implementation.

## 1. Documentation Created

I created a new directory `docs/learning/` and populating it with the following guides:

*   **[Trade Metrics Guide](learning/trade-metrics.md)**
    *   **Purpose**: Explains how to calculate key metrics like Win Rate and Profit Factor.
    *   **Key Insight**: Clarifies how to handle "Campaigns" (rolls) vs individual trades to avoid muddying the win rate with necessary hedging losses.

*   **[Opportunity Scoring Rubric](learning/opportunity-scoring.md)**
    *   **Purpose**: Defines a 0-100 scoring system for potential trades.
    *   **Key Factors**: IV Rank (40%), Technical Trend (30%), Liquidity (20%), Yield (10%).

*   **[Juicy Thresholds](learning/juicy-thresholds.md)**
    *   **Purpose**: Sets the hard "Line in the Sand" for what constitutes a "Juicy" trade.
    *   **Values**: IV Rank > 50, Delta 0.30-0.40, Market Cap > $2B.

*   **[Kalman Filters in Trading](learning/kalman-filters.md)**
    *   **Purpose**: Explains the math and application of Kalman Filters.
    *   **Use Case**: Dynamic hedge ratios for pairs trading and trend following signal generation.

*   **[Backtesting Engines](learning/backtesting-engines.md)**
    *   **Purpose**: Compares Vectorized vs Event-Driven engines.
    *   **Decision**: Recommends an **Event-Driven** approach (Zipline, Backtrader, or Custom) to properly handle options lifecycle (assignment/exercise/rolls).

*   **[Agent Frameworks](learning/agent-frameworks.md)**
    *   **Purpose**: Discusses how to build the "Antigravity" agents.
    *   **Strategy**: Hybrid approach using **LangChain** for the "Brain" (orchestration/chat) and **Lumibot** for the "Body" (execution/risk).

*   **[Bad Trade Heuristics](learning/bad-trade-heuristics.md)**
    *   **Purpose**: Codifies rules to prevent emotional or risky trading.
    *   **Rules**: Blocks 0DTE selling, Earnings gambles, and "Revenge Trading".

## 2. Requirements Update

I updated `docs/features-requirements.md` to:
1.  Link the original "Learning Opportunity" items to these new documents.
2.  Mark those items as `[x]` (Done) or `REFINED` where appropriate.

## 3. Next Steps (UX/UI Implications)

Based on this research, the following future tasks are enabled:

*   **Tooltips**: Use the content from `trade-metrics.md` to populate UI tooltips in the Trade History view.
*   **Scoring Column**: Implement the logic from `opportunity-scoring.md` in the Backend to add a "Juicy Score" column to the Opportunity Finder grid.
*   **Filter Logic**: Hard-code the `juicy-thresholds.md` values into the scanner API.
