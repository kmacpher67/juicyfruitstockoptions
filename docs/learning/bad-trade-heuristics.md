# Bad Trade Heuristics ("Ken's Bad Trades")

A set of hard rules/heuristics to block or warn against trades that historically lead to "Blowing up the account."

## 1. The "Impatience" Trade (Chasing)
*   **Definition**: Trying to enter a trade when the price has already moved significantly away from the mean.
*   **Heuristic**: Warning if entering a Long Call when RSI > 75 (15min or Hourly).
*   **Heuristic**: Warning if entering trend position if Distance_From_20SMA > 3 * ATR.

## 2. The "Gamma Risk" Trade (0DTE)
*   **Definition**: Selling options expiring today (0 Days To Expiration).
*   **Risk**: A small move in the underlying stock can result in a 500% loss on the option in minutes.
*   **Rule**: Soft Block on selling options with `< 3 DTE` unless specifically flagged as a "Lotto" account.

## 3. The "Earnings Gamble"
*   **Definition**: Selling premium right before an earnings announcement.
*   **Risk**: "IV Crush" works in your favor, but a "Gap Move" (stock moves 20% overnight) can blow through your strike and wipe out months of gains.
*   **Rule**: No Short Strangles/Straddles through earnings. Defined Risk (Spreads/Iron Condors) only.

## 4. The "Liquidity Trap"
*   **Definition**: Trading options with no volume.
*   **Risk**: You enter for $1.00. You want to leave. Bid is $0.50, Ask is $1.50. You instantly lose 50% just to exit.
*   **Rule**: Reject order if `Spread Width > 10% of Mid Price`.

## 5. Over-allocation
*   **Definition**: Putting 50% of account into TSLA calls.
*   **Rule**: Warning if `Max Loss > 5% of Net Liquidation Value`.

## 6. The "Revenge Trade"
*   **Definition**: Opening a new position on Ticker X immediately after closing Ticker X for a loss.
*   **Rule**: "Cool off" timer. Warning if opening same-ticker trade within 30 mins of a loss > $500.

Details from Gemini discussion: 

In the context of evaluating a portfolio, **Risk Type** categorizes the specific *source* of potential loss. Understanding the "why" behind a risk allows you to determine whether the correct action is to hedge, exit, or double down.

---

## 1. Execution Risk

This occurs at the moment of the trade. It’s the risk that you are "losing" money simply by entering the market due to poor liquidity.

* **What it means:** High slippage or wide bid-ask spreads.
* **Trading Recommendation:** * **Action:** **Avoid or Limit Order.**
* **Strategy:** Never use "Market Orders" on low-volume options. If the spread is too wide, **walk away**. If you must trade, use a "Mid-point Limit Order" and wait for the fill.



## 2. Tactical (Event) Risk

This is the risk tied to a specific "binary" event where the outcome is unpredictable (like an earnings report or a court ruling).

* **What it means:** You are exposed to "IV Crush"—where volatility drops instantly after the news, causing option prices to plummet even if the stock doesn't move.
* **Trading Recommendation:**
* **Action:** **Create a Non-Directional Play.**
* **Strategy:** Instead of "buying" a call (high risk), **Sell a Covered Call** or a **Credit Spread** to harvest the high volatility premium before the event. If you are long the stock, consider a **Protective Put** (Married Put) to floor your losses.



## 3. Opportunity Cost (Efficiency) Risk

This measures the risk of your money "sitting still" or underperforming.

* **What it means:** Your capital is tied up in a "Zombie Trade" that isn't hitting your target annualized yield.
* **Trading Recommendation:**
* **Action:** **Sell/Exit.**
* **Strategy:** Close the position and move the capital into a higher-yielding setup. It is better to take a small loss or break even to free up "buying power" for a trade with a better **Annualized Yield**.



## 4. Account Survival (Systemic) Risk

This is the "Game Over" risk. It’s when a single trade or a market-wide crash could wipe out your account or trigger a margin call.

* **What it means:** Over-leverage or lack of diversification.
* **Trading Recommendation:**
* **Action:** **Hedge or Trim.**
* **Strategy:** **Sell** a portion of the position to bring the "Size" back under 2% of your net liquidity. Alternatively, **Create a Put Option Play** (specifically a "Tail Hedge") on a broad index like SPY or QQQ to protect the entire portfolio from a "black swan" event.



---

### Summary Recommendation Table

| Risk Type | Indicator | Primary Recommendation |
| --- | --- | --- |
| **Execution** | Wide Spreads | **Wait/Limit Order** |
| **Tactical** | High IV/Earnings | **Sell Premium (Call/Put Spreads)** |
| **Opportunity** | Low Annualized Yield | **Exit/Reallocate** |
| **Survival** | High Beta-Delta/Margin | **Trim Position or Buy Protective Puts** |
