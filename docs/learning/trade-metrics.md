# Trade Metrics and Calculations

This document explains the key performance indicators (KPIs) used in the Juicy Fruit Trade History view. It clarifies how metrics are calculated and how complex scenarios like diagonal rolls and dividends are handled.

## Core Metrics

### Win Rate
The percentage of closed trades that resulted in a profit.

*   **Formula**: `(Count of Winning Trades / Total Count of Closed Trades) * 100`
*   **Definition of Win**: A trade where `Realized P&L > 0`.
*   **Breakeven**: Trades with exactly $0 P&L are typically excluded from the win count but included in the total, or counted as a "scratch" depending on strictness. For now, we treat `> 0` as a win.

### Profit Factor
A measure of the gross profitability of your system. It answers: "For every dollar lost, how many dollars were made?"

*   **Formula**: `Gross Profit / Abs(Gross Loss)`
*   **Gross Profit**: Sum of all positive Realized P&L.
*   **Gross Loss**: Sum of all negative Realized P&L (absolute value).
*   **Interpretation**:
    *   `> 1.0`: Profitable system.
    *   `> 1.5`: Good system.
    *   `> 2.0`: Excellent system.
    *   `< 1.0`: Losing system.

### Average Trade P&L
The mathematical expectation of the system per trade.

*   **Formula**: `Total Realized P&L / Total Count of Closed Trades`

## Complex Scenarios

### Diagonal Rolls
A "Diagonal Roll" (or "Rolling") involves closing an existing position (usually a short call) and opening a new one at a different strike and/or expiration. This often involves realizing a loss on the short leg to keep the upside alive or to collect more premium over time.

*   **Impact on Metrics**:
    *   **Realized Loss**: The leg being closed for a loss results in a realized loss, which negatively hits "Win Rate" and "Gross Loss".
    *   **Unrealized Gain**: The underlying stock or long option leg may have gained significant value. This is *unrealized* until the entire campaign is closed.
*   **Metrics Distortion**: Rolling often makes the "Win Rate" look worse (sequence of small realized losses) while the "Net Liquidation Value" (NAV) of the portfolio increases.
*   **Recommendation**:
    *   Track **"Campaign P&L"**: Group all related trades (the initial buy, all rolls, final close) into a single "Campaign" ID.
    *   The "Win Rate" of Campaigns is a more accurate reflection of strategy success than the "Win Rate" of individual option legs.

### Dividends
Dividends are cash inflows that improve the return of a stock holding but are technically separate from capital gains.

*   **Handling**:
    *   **Total Return**: Must include Dividend payments.
    *   **Cost Basis Adjustment**: Some traders prefer to subtract dividends from the cost basis of the stock (adjusted cost basis), making the final sale appear more profitable.
    *   **Separate P&L Bucket**: Others adhere to strict accounting where Dividends are "Income" and Trade P&L is "Capital Gains".
*   **Conclusion for Juicy Fruit**: Keep Dividends as a separate line item in "Income" but include them in the "Total Portfolio Return" metric. Do not incorrectly adjust trade P&L (Capital Gains) with Dividends unless calculating "Adjusted Cost Basis" for personal psychological tracking.

### Assignment & Exercise
*   **Assignment (Short Call)**: The stock is called away.
    *   **Trade Closure**: The stock position is closed. The Call option is closed (expires or is bought back at intrinsic).
    *   **P&L Calculation**: `(Strike Price - Original Stock Cost) + Premium Received`.
*   **Assignment (Short Put)**: Stock is put to you.
    *   **New Position**: Opens a new Stock position.
    *   **Cost Basis**: `Strike Price`. (Some adjust this by the premium received: `Strike - Premium`).
