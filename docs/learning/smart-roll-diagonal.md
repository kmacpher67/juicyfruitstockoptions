# Smart Roll & Diagonal Spread Strategies

**Topic**: Option Rolling Strategies (Calendar & Diagonal)
**Audience**: Trader Ken & Agent Developers
**Purpose**: Define the logic, goals, and implementation details for the "Smart Roll Assistant" feature.

---

## 1. First Principles: What is a "Roll"?

In options trading, a "roll" is the act of closing an existing position (buying back a short option) and simultaneously opening a new position (selling another short option) in the same underlying asset with a different expiration date and/or strike price.

It is executed as a single **spread order** to ensure both legs fill at the desired net price (Credit or Debit).

### The Math
$$ \text{Net Price} = \text{Premium Sold (New)} - \text{Premium Paid (Old)} $$

*   **Net Credit**: You receive money. This is the goal for income strategies.
*   **Net Debit**: You pay money. Usually avoided unless defending a position aggressively.

---

## 2. Strategies

### A. Calendar Roll (Horizontal)
*   **Action**: Buy back current short option, Sell new option at the **SAME Strike**, **LATER Date**.
*   **Goal**: Buy more time for the trade to work. Collect more external value (Time value).
*   **Best For**: When the stock is challenging your strike but you believe it will settle or pull back, and you want to maintain the same strike price.

### B. Diagonal Roll (Up/Down and Out)
*   **Action**: Buy back current short option, Sell new option at a **DIFFERENT Strike**, **LATER Date**.
    *   **Up and Out (Calls)**: Move strike HIGHER (further OTM).
    *   **Down and Out (Puts)**: Move strike LOWER (further OTM).
*   **Goal**: Improve the strike price (give the stock more room to move) while still collecting a credit (or paying a very small debit).
*   **Best For**: When the stock has moved against you (e.g., rallied past your short call) and you want to "rescue" the position by moving the goalposts, potentially realizing value from the underlying stock appreciation.

---

## 3. The "Juicy Fruit" Logic

For this project, we prioritize **Short Duration** and **Net Credit**.

### Strategic Objectives
1.  **Reduce Assignment Risk**: Move the option out in time to avoid immediate assignment.
2.  **Improve Strike**: Move the strike away from the current price (OTM) to unlock "trapped" capital gains in the underlying shares.
3.  **Generate Income**: Ideally, the roll should result in a **Net Credit**. We are paid to wait.

### Heuristics (The Rules)

#### A. Duration Control
*   **Preference**: Short duration rolls.
*   **Target**: `< 10 Days` added expiration. (e.g., Roll from this Friday to next Friday).
*   **Rationale**: We want to keep Theta (time decay) high. Going out 45+ days slows down the daily decay.

#### B. The "Smart Roll" Scoring Rubric
How do we determine if a roll is "Good"? We assign a score (0-100).

| Factor | Weight | Condition | Bonus/Penalty |
| :--- | :--- | :--- | :--- |
| **Net Credit** | 40% | Must be $> 0$. | +Score for higher relative credit. Penalty for Debit. |
| **Strike Improv** | 30% | New Strike $>$ Old Strike (for Calls). | +Score per strike increment. |
| **Duration** | 20% | Days Added. | +Score for shorter duration (Keep it tight!). |
| **Protection** | 10% | Distance form Current Price. | +Score if New Strike $>$ Current Stock Price (OTM). |

#### C. Implementation Logic (Python Snippet)

```python
def score_roll(roll, current_position):
    """
    roll: {net_credit, new_strike, days_extended}
    current: {strike, average_cost}
    """
    score = 50 # Base

    # 1. Credit Factor
    if roll['net_credit'] > 0:
        score += 20 # Paid to wait!
        # Bonus for "Juicy" Yield (e.g. > 1% of strike)
        if roll['net_credit'] / roll['new_strike'] > 0.005: 
            score += 10
    elif roll['net_credit'] < 0:
        score -= 20 # Paying is bad
    
    # 2. Strike Factor (Up and Out)
    strike_diff = roll['new_strike'] - current['strike']
    if strike_diff > 0:
        score += 20 # Better strike!
        # Bonus: Unlocks unrealized stock gains?
        # If current price > old strike, moving up realizes that gain.
    
    # 3. Duration Factor
    if roll['days_extended'] <= 7:
        score += 10 # Perfect weekly roll
    elif roll['days_extended'] > 21:
        score -= 10 # Too far out (slow Theta)

    return min(100, max(0, score))
```

---

## 4. References & Citations

*   **Investopedia - Rolling Options**: [Link](https://www.investopedia.com/terms/r/rollingover.asp)
*   **Options Playbook - Diagonal Spread**: [Link](https://www.optionsplaybook.com/option-strategies/diagonal-call-spread/)
*   **Tastytrade - Rolling Logic**: Strategies often focus on rolling for a credit to reduce cost basis.

---

## 5. Next Steps for Agent
1.  Update `RollService.find_rolls` to enforce the 10-day duration preference.
2.  Implement the scoring logic defined above.
3.  Expose these recommendations in the UI under specific "Smart Roll" alerts.


--- 

## More Notes from Gemini in web browser: 

Building a tool for rolling short options—especially within a tight **7-day window**—requires a shift from "passive management" to "active defense." At that proximity to expiration (Gamma risk zone), the math changes rapidly.

Since you are focusing on the 0–7 day range, here is how to optimize your logic and the variables you should integrate to make the "Smart Roll" truly intelligent.

---

## 1. Defining the "Optimum" Window

While 10 days is the standard industry "warning" flag, **7 days is the execution sweet spot** for weekly traders.

* **The Sweet Spot:** Roll between **DTE 2 and DTE 4**.
* **The Why:** Theta decay (time decay) is non-linear. It accelerates most aggressively in the final week, but so does **Gamma** (the risk that a small move in the stock causes a massive move in the option price). Rolling too early leaves money on the table; rolling too late (DTE 0-1) makes you a victim of "pin risk" and massive slippage.

---

## 2. Critical Variables: Moneyness and "The Level Out"

When rolling, "Strike Improvement" isn't just about moving the strike up; it’s about managing the **Delta** and the **Probability of Profit (PoP)**.

| Variable | Importance for Rolling | Impact on Logic |
| --- | --- | --- |
| **Delta** | Extreme | If your short call has a Delta > 0.60, it’s "deep in the fight." Your roll should aim to reset the new position to a **0.20 - 0.30 Delta**. |
| **IV Rank / Skew** | High | If Call Skew is high (bullish bias), you can get paid more to move further OTM. If Skew is flat, you might have to stay closer to the money to get a credit. |
| **Implied Volatility (IV) Crush** | Tactical | If an earnings event or news drop is within your 7-day window, the "Roll Yield" is artificial. You must adjust the score downward if IV is expected to collapse post-event. |
| **Gamma Risk** | Critical | Near DTE 0, Gamma is at its peak. Your `score_roll` should penalize holding positions where the underlying price is within **1-2% of the strike**. |

---

## 3. Enhancing the `score_roll` Logic

To make your agent smarter, don't just look at the credit. Integrate these technicals into your 0-100 score:

### **The "Roll Efficiency" Formula**

Instead of just "Higher Credit = Higher Score," use a **Risk-Adjusted Credit** metric.


### **Technical Filters to Add:**

* **TSMOM (Time Series Momentum):** If TSMOM is strongly positive and you are rolling a Short Call, the tool should suggest a **wider strike improvement** (more OTM) because the "train" isn't stopping.
* **RSI/EMA:** If RSI is > 70 (Overbought), the score for rolling to a *slightly* OTM strike should be higher, as a mean reversion is likely, allowing you to keep more premium.
* **Annualized Return (ROC):** You must compare the capital tied up.
* *Formula:* `(Credit / Strike) * (365 / Days to Expiration)`.
* Aim for an annualized ROC of > 20% to justify the risk of the roll.



---

## 4. Proposed Logic Adjustments

### **Updated `find_rolls` Priorities**

1. **Defensive Roll:** If `Underlying > Strike` (In the Money), prioritize "Strike Improvement" even if the credit is small. The goal is to avoid assignment.
2. **Aggressive Roll:** If `Underlying < Strike` (Out of the Money), prioritize "Credit Harvest." Roll for the maximum premium while keeping the Delta under 0.30.

### **The "Gamma Penalty"**

Add a logic gate: If `DTE < 2` and `Moneyness > 0.98`, trigger an **"Urgent Roll"** status. This should override standard scoring because the risk of a gap-up/down overnight outweighs the benefit of waiting for more Theta decay.

--- 

## additional notes from Gemini (part 2):

### Question asked to Gemini: 
One of the variables i look at when I"m in the current week expire window is current day 1 day momentum, on a covered (- sold) CALL is the stock up? and it's Weds before the Fri is that a DTE 2 , then I might ROLL that day or if the stock current trend is down. then I'll wait for 1 DTE (ie thursday).

Additionally, if the stock is trending down. I might move a DEEP OTM position 1 week and just a little up the keeping the downward coverage. Sometimes I'll even consider just buying the OPT back even at a loss if the DROP is low enough and the over-all trend indicates I can sell a new COVERED CALL the following day for a much better position. What would that look like for me to update the directions or explaination in my feature learning anti-gravity agent document?

### Answer from Gemini: 

This logic is what separates a basic script from a professional-grade trading "Anti-Gravity" agent. You are essentially building a **Conditional Momentum Overlay** for your rolling logic.

To update your documentation or "Feature Learning" document, you need to define the **Decision Matrix** that governs how the agent handles the 0-7 DTE window based on the 1-day momentum and the underlying trend.

---

### 1. Updated Logic: The "Momentum-Based Roll Trigger"

In your documentation, define the relationship between **DTE** and **1-Day Δ (Delta of the stock price)**.

* **Bullish Momentum (Stock Up + DTE 2):** * *Logic:* If today is Wednesday (DTE 2) and the stock is up, the agent triggers an **Immediate Roll**.
* *Reasoning:* You want to capture the remaining extrinsic value before Gamma makes the "Buy to Close" (BTC) cost too volatile.


* **Bearish Momentum (Stock Down + DTE 2):** * *Logic:* If the stock is trending down, the agent triggers a **"Hold & Harvest"** state. It shifts the target execution to Thursday (DTE 1).
* *Reasoning:* You are letting the downward momentum (and Theta) crush the premium further, making the roll or buy-back cheaper.



---

### 2. The "Defensive Buy-Back" (Anti-Gravity Maneuver)

You mentioned buying back at a loss to reposition. In your document, define this as the **"Reset Protocol"**.

* **Trigger:** If `Current Price < Strike` AND `Trend = Strong Bearish`.
* **Action:** If the BTC cost is low enough (e.g., < 10% of the original credit received), the agent suggests closing the position entirely without an immediate roll.
* **The "Wait & Strike" Rule:** The agent flags the ticker for a **"Re-Entry Scan"** the following morning. It looks for a "Green Day" or a bounce off an EMA to sell the *next* week's Call at a higher premium.

---

### 3. Proposed Updates for your Agent Document

You can copy and adapt these sections into your technical specs:

#### **Feature: Dynamic DTE Scaling**

> "The agent shall adjust the `Target_Roll_Date` based on `1D_Stock_Momentum`. If momentum is positive, `Target_Roll_Date = DTE 2`. If negative, `Target_Roll_Date = DTE 1` to maximize Theta extraction."

#### **Variable: Downward Coverage Bias**

> "When rolling in a bearish trend, the agent shall prioritize **Strike Preservation** over **Credit Max**. It will favor a 'Roll Down and Out' (moving the strike closer to the current price while extending 7 days) only if the `Annualized_Yield` remains above your 25% target."

---

### 4. How this impacts your `score_roll`

To implement this, your `score_roll` helper needs two new inputs: `one_day_momentum` and `primary_trend`.

| Condition | Score Adjustment | Recommended Action |
| --- | --- | --- |
| **Up Day + DTE 2** | +20 points to "Roll Now" | Secure the roll before the strike is challenged further. |
| **Down Day + DTE 2** | -20 points to "Roll Now" | Wait. Let the premium bleed out until Thursday. |
| **Deep OTM + Bearish** | +15 points to "Roll & Lower" | Capture "Downward Coverage" by lowering the strike for better future premium. |

---


