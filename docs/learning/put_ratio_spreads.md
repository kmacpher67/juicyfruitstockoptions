# Buy stock using PUT ratio spread

**GOAL:** 
want to buy a stock not sure it's the low price you want but won’t touch it at current prices, consider a put ratio spread. DTE 14-30 days

Buy STK stock using PUTs ratio spread
At 11:30am Friday 4/10/2026
STK price ~$471 change is NEG or moving downward 
you want to buy a stock consider a put ratio spread. DTE 14-30 days
Buy 1 nearest ITM 
Sell 2 nearest OTM 

WHEN:  STK current movement is stalled, NEG, moving strongly DOWNWARD. 

Example: buy 1 put above your level, sell 2 puts at your level.

If it drops but doesn’t reach your price → you make money.
If it drops to your price → you get assigned and buy it where you wanted.
If it goes up → you weren’t buying anyway.

This isn’t about adding leverage. It’s a way to reduce risk and use options as a mechanism to either get paid to wait or buy the stock at your price-nothing more.

--- 
# Wheel Strategy vs Put Ratio Spread 
Based on your project documentation and the specific scenario described, here is an analysis of how the standard Wheel Strategy (Phase 1) differs from using a **Put Ratio Spread** to enter a position.

## Strategy Comparison: Wheel vs. Put Ratio Spread

| Feature | Standard Wheel (Phase 1: CSP) | Put Ratio Spread (1x2) |
| :--- | :--- | :--- |
| **Primary Goal** | Generate premium income while waiting to be assigned at a single strike. | "Get paid to wait" or buy at a specific target price while hedging the entry. |
| **Structure** | Sell 1 Cash-Secured Put (Short Put). | Buy 1 ITM Put + Sell 2 OTM Puts (Short 1 Net). |
| **Upward Move** | Keep the premium; no stock ownership. | Keep the net credit (if any); no stock ownership. |
| **Slight Drop** | Premium decays; trade remains profitable. | The Long Put gains value faster than the Short Puts initially, often increasing profit. |
| **Drop to Target** | Assigned at the strike price. | Assigned at the short strike, but the cost basis is lowered by the profit of the long put. |

---

## Technical Differences for MSFT Example
**Scenario Context**: STK price ~$471 | DTE 14–30 days.

### 1. Risk Mitigation and Cost Basis
* **The Wheel**: If you sell a 460 Put, you are assigned at 460. Your cost basis is $460 - \text{Premium Received}$.
* **Put Ratio Spread**: By buying 1 ITM Put (e.g., 475) and selling 2 OTM Puts (e.g., 460), the "Buy 1" leg acts as a buffer. If MSFT drops to your 460 level, the 475 Put you bought is worth significantly more, which offsets the cost of the assignment. This effectively reduces the risk and lowers the purchase price more than a single short put would.

### 2. The "Sweet Spot"
* In a **Put Ratio Spread**, you reach maximum profit if MSFT pins exactly at your "Sell 2" strike (460).
* In the **Wheel Strategy**, profit is capped at the premium received regardless of how close to the strike the stock ends, provided it stays OTM.

### 3. Margin and "Nothing More" Philosophy
* You noted this isn't about leverage. In your local environment, this is treated as an **entry mechanism**.
* While a standard Wheel is a "Short" seller strategy focused on yield, the Ratio Spread is a "Business Trader" tool used to manage entry timing for your light manufacturing and engineering business cash flows.

---

## Workspace Implementation
To track these differently in **Juicy Fruit**, consider these updates to your scanner logic:

### Proposed Scanner Logic
* **Phase 1 (Standard)**: Use the `CSP_Optimizer` to find high IV Rank Puts (Delta 0.20–0.30) for simple entry.
* **Ratio Entry Mode**: Update the `Juicys Workspace` to identify tickers with high `TSMOM_60` but temporary price dips, where a 1x2 Ratio Spread offers a "Juicy" cost basis reduction compared to a flat limit order.

### Deployment Note
Since your system is currently **Level 0 Autonomy**, these will appear as recommendations in the **Opportunity Finder**. You would then manually review the Greeks (Delta/Gamma) in the `TickerModal` before executing in IBKR.
