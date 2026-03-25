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

### Total Trades (Open vs Closed)
Understanding trade counts is essential for analyzing the scope of the portfolio.

*   **Total Trades**: The sum of all active (`Open`) and completed (`Closed`) trades.
*   **Closed Trades**: Trades that have realized P&L, such as selling a stock you own or buying back a short option. Win Rate and Profit Factor are calculated strictly on Closed Trades.
*   **Open Trades**: Initiating trades that have not yet realized P&L. They exist in the portfolio's FIFO queue and represent current risk/exposure.

### Realized vs Unrealized P&L
*   **Realized P&L**: Profit or loss that has been "locked in" by completely or partially closing an existing position (e.g., selling long shares, covering short shares). This value is locked on the date the trade is closed.
*   **Unrealized P&L**: Theoretical profit or loss if all currently *Open Trades* were to be closed at the current market price. This dynamically updates based on live market data and represents the "paper" profit/loss.

## Time Selector Filtering

The Trade History view allows you to filter metrics by a specific time frame (e.g., YTD, 30 Days, Custom Range). The way the system calculates P&L when a time filter is applied is specifically designed to ensure accuracy:

1.  **Full History FIFO Calculation**: The system first loads *all* trades across the account's history and calculates P&L using a First-In-First-Out (FIFO) queue. This is necessary because an opening trade from last year might be closed this year, and we must match them correctly.
2.  **Filtering Realized P&L**: After the full FIFO calculation is complete, the resulting `AnalyzedTrades` are filtered by the selected date range. Only trades that *occurred* within the selected time window will contribute to the Realized P&L, Win Rate, and Profit Factor metrics.
3.  **Filtering Unrealized P&L**: The system filters the current *open position lots* based on the selected date range. Only position lots that were *opened* within the selected time window will be included in the Unrealized P&L calculation. This means evaluating "YTD" Unrealized P&L will show you the paper profit/loss strictly for positions initiated this calendar year, ignoring underlying stock you bought three years ago.
4.  **Market Data**: Unrealized P&L is calculated instantly utilizing cached market prices from the most recent portfolio snapshot (`ibkr_holdings`), drastically improving load times over real-time external API calls.

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
