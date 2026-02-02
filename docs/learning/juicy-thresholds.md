# Juicy Thresholds

This document defines the specific quantitative "Line in the Sand" values that qualify a trade as "Juicy." These are hard filters used to scan the universe of thousands of tickers down to a manageable watchlist.

## 1. Volatility Filters (The "Juice")
*   **IV Rank**: `> 50`
    *   *Why?* We want to sell mean-reverting volatility.
*   **IV Percentile**: `> 50%`

## 2. Option Greeks (The Structure)
For **Covered Calls** and **Short Puts** (The Wheel):
*   **Delta**: `0.30` to `0.40`
    *   *Why?* This strikes a balance between collecting meaningful premium and having a probability of profit (POP) of ~60-70%.
    *   *Aggressive*: `0.45` Delta (More premium, higher assignment risk).
    *   *Conservative*: `0.20` Delta (Less premium, lower assignment risk).
*   **Theta**: Positive (we are selling time).

## 3. Liquidity (The Safety)
*   **Stock Volume**: `> 1,000,000` (daily average).
*   **Option Open Interest**: `> 500` contracts at the specific strike.
*   **Bid/Ask Spread**: `< $0.10` or `< 5%` of the bid price.
    *   *Why?* Wide spreads kill profitability and make it hard to roll or exit.

## 4. Fundamental Quality (The Asset)
Since we might own the stock (Covered Call) or be forced to buy it (Short Put), we must be willing to hold it.
*   **Market Cap**: `> $2 Billion` (Mid/Large Cap). avoid penny stocks.
*   **Earnings**: Avoid opening short volatility positions `3 days before` or `1 day after` earnings releases (Binary event risk).

## 5. Return Targets
*   **Minimum Premium**: `$0.50` (absolute dollars).
    *   Selling options for $0.10 is rarely worth the commission and risk.
*   **Annualized Return**: `> 20%`.
