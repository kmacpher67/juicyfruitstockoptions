Evaluating 0DTE (Zero Days to Expiration) or near-dated out-of-the-money (OTM) options requires shifting your focus from "value" to "probability of touch." When options are hours or a few days from expiring, the relationship between the current price and the strike becomes extremely non-linear.

## 1. Filtering: Percentage vs. Dollar Amount
The "best" way to filter depends entirely on the **volatility (ATR)** of the underlying asset.

* **Dollar Amount ($):** Best for low-priced stocks (e.g., under $50) or consistently low-volatility assets. A $2.00 move on a $20 stock is a 10% swing, whereas on SPY, it's less than 0.5%.
* **Percentage (%):** Generally the superior filter for a broad watchlist, as it scales with the stock price. However, you must adjust your "in play" threshold based on the **Average True Range (ATR)**. 

### The ">1% Unlikely" Threshold
Statistically, for a standard equity index or a mega-cap stock with average IV, a strike that is **>2% to 3% OTM** on the day of expiration is generally considered "unlikely" to be tested (roughly a 1-standard deviation move). 
* **The 1% Rule:** If a stock is trading at $100, a $101 strike (1% OTM) is very much "in play." 
* **The Gamma Trigger:** Options usually start "feeling" the price movement significantly when they are within **0.5% to 1%** of the strike. This is where Delta accelerates the most.

---

## 2. The Role of the Greeks and Volatility
In 0DTE scenarios, the Greeks behave like high-tension springs. 

### Delta as a Probability Proxy
Delta is your most efficient filter for "likelihood of exercise."
* **Delta < 0.10:** Deep OTM. These are the "lottery tickets." High probability of expiring worthless.
* **Delta 0.15 – 0.30:** The "Danger Zone." These are the options most likely to see a massive percentage spike if the trend moves toward them.
* **Delta > 0.40:** High probability of moving At-The-Money (ATM) or In-The-Money (ITM) before the bell.

### Gamma: The Engine of 0DTE
Gamma is at its absolute peak when an option is near expiration and near the money. It represents the rate of change in Delta.
* If you are tracking options "likely in play," you are looking for **high Gamma**. A small move in the stock price will cause the Delta to explode, making the option price move almost dollar-for-dollar with the stock.

### Theta and IV (The Crush)
* **Theta:** On expiration day, Theta is terminal. The extrinsic value decays by the minute.
* **Vega/IV:** If IV is crushing (decreasing) after an event like earnings, even a move toward your strike might not result in a price gain because the "volatility premium" is evaporating faster than the price is helping.

---

## 3. Practical Filtering Strategy
To focus only on options likely to be exercised or "in play," use these specific screener settings:

| Metric | Target Setting | Reason |
| :--- | :--- | :--- |
| **Days to Expiration** | 0 to 2 Days | Focuses on immediate gamma risk/opportunity. |
| **Delta** | 0.20 to 0.45 | Filters out "dead" options and identifies those gaining steam. |
| **% OTM** | < 1.5% | Keeps the strike within a reasonable daily trading range. |
| **Volume/Open Interest** | > 500 | Ensures liquidity so you aren't trapped by a wide Bid/Ask spread. |



### Pro-Tip: The "Expected Move"
Check the **Market Expected Move** (often displayed in platforms like ThinkOrSwim or Interactive Brokers). If the market expects a $5.00 move today, any strike within $5.00 of the current price is "in play." Anything outside that range is mathematically an outlier.

Would you like me to help you draft a specific scanner query for Interactive Brokers to find these 0DTE opportunities?

