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
