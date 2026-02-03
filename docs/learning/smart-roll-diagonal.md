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
*   **Net Debit**: You pay money to roll. While often avoided, this is a high-value move when "Rolling Up" on a trending stock.
    *   **The "Unlocking" Math**: You are paying cash now to unlock significantly more value in the underlying stock.
        *   *Example*: You pay a **$0.50 Debit** to roll your Call Strike up by **$2.50**.
        *   *Result*: You "paid" $0.50 to create room for $2.50 of stock appreciation. Your net potential gain increases by **$2.00**.
        *   $$ \text{Value Created} = (\text{New Strike} - \text{Old Strike}) - \text{Net Debit} $$
    *   **Tax Efficiency (The "Hold" Bonus)**: Paying a debit to avoid assignment allows you to keep the underlying shares. In taxable accounts, extending the holding period from < 1 year (Short Term Cap Gains) to > 1 year (Long Term Cap Gains) can save 15-20% in taxes, far outweighing the cost of the debit roll.
    *   **MTM Impact**: Your Net Liquidating Value (NLV) rises immediately because the "cap" on your stock is lifted, even if the cash balance drops slightly.



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


---

## 4. Advanced "Anti-Gravity" Logic

To move from basic arithmetic to "Smart" rolling, we overlay **Momentum** and **Gamma Risk** logic. This adapts the strategy based on the market's immediate behavior (Velocity).

### A. The "Optimum" Execution Window
While 10 days is the warning zone, the **7-day window** is the execution zone.
*   **Sweet Spot**: DTE 2 to DTE 4 (Wednesday/Thursday for a Friday expiry).
*   **Physics**: Theta decay accelerates here, but so does Gamma. 
    *   **Goal**: Capture maximum decay without getting pinned (Gamma risk).

### B. Dynamic DTE Scaling (Momentum Trigger)
The target roll date is not fixed; it reacts to the stock's 1-day momentum (`1D % Change`).

| Scenario | Logic | Action | Rationale |
| :--- | :--- | :--- | :--- |
| **Bullish (Stock UP) + DTE 2** | `Price > Strike` (ITM) and Trending Up. | **Immediate Roll** (Wed). | Gamma Risk is high. Capture remaining extrinsic value before the "Buy to Close" cost spikes due to delta expansion. |
| **Bearish (Stock DOWN) + DTE 2** | `Price > Strike` (ITM) but Trending Down. | **Hold & Harvest**. Wait for DTE 1 (Thu). | Momentum is helping you. Let the price drop and Theta crush the premium further. |
| **Neutral / Choppy** | `Price ~ Strike` (ATM). | **Standard Roll**. | Execute based on best Credit/Yield available. |

### C. The "Gamma Penalty" (Urgent Roll)
*   **Trigger**: `DTE < 2` AND `Moneyness > 0.98` (Price is within 2% of Strike or ITM).
*   **Action**: **Urgent Roll**. Override standard scoring. 
*   **Why**: Pin risk is imminent. A small gap up tomorrow could lead to max loss or unwanted assignment. 

### D. The "Defensive Buy-Back" (Reset Protocol)
Sometimes the best roll is ... stopping. 
*   **Trigger**: `Current Price < Strike` (OTM) AND `Trend = Strong Bearish`.
*   **Action**: **Close Position (BTC)**. Do not open a new leg immediately.
*   **Logic**: If the BTC cost is low (< 10% of max profit), take the win. The trend suggests calls will be cheaper tomorrow or next week on a bounce. 
*   **The "Wait & Strike" Rule**: Flag ticker for "Re-Entry Scan". Look for a green day or EMA bounce to resell the call.

---

## 5. Scoring Algorithm Assessment
The pythonic scoring method (`score_roll`) combines these factors.

### Updated Metrics & Weights

| Factor | Weight | Condition | Bonus/Penalty |
| :--- | :--- | :--- | :--- |
| **Net Credit** | 30% | Must be $> 0$. | +Score for high Yield (Credit/Strike). |
| **Strike Improv** | 20% | New Strike $>$ Old Strike. | +Score for moving OTM. |
| **Duration** | 20% | Days Added < 10. | +Score for short rolls. |
| **Momentum** | 20% | Bullish & Rolling Up vs Bearish & Holding. | +20 for "Up Day + DTE 2 + Roll Up". |
| **Gamma/Delta** | 10% | Delta Risk. | -Score if New Delta > 0.60 (Still ITM). |

### Conceptual Python Implementation
*This extends the basic logic to include market dynamics.*

```python
def score_roll(roll, current_pos, market_data, dividend_info=None):
    score = 50.0 # Base

    # Context
    dte = roll['days_to_expiry_current'] # DTE of OLD position
    one_day_chg = market_data.get('one_day_change', 0)
    is_itm = market_data['current_price'] > current_pos['strike']
    
    # --- 1. Momentum & Timing (The "Smart" Layer) ---
    
    # SCENARIO: Bullish + DTE 2 (Wednesday)
    if one_day_chg > 0.5 and dte <= 2:
        if roll['roll_type'] == "Up & Out":
            score += 25 # URGENT: Lock in the roll now before it runs away!
            
    # SCENARIO: Bearish + DTE 2
    elif one_day_chg < -0.5 and dte <= 2:
        # We prefer to WAIT. So "Rolling Now" is slightly penalized unless it's a "Rescue" for a deep ITM.
        if not is_itm:
             score -= 15 # Wait! Let it bleed.
             
    # --- 2. Gamma Penalty ---
    if dte < 2 and (market_data['current_price'] / current_pos['strike']) > 0.98:
        # Urgent Risk.
        score += 10 # Prioritize ANY roll that solves this, specifically Up & Out.
        if roll['new_strike'] <= current_pos['strike']:
            score -= 50 # Rolling to same/lower strike in Gamma zone is suicide.

    # ... (Standard Credit/Strike logic follows) ...
    
    return max(0, min(100, score))
```

---

## 6. References & Citations

*   **Investopedia - Rolling Options**: [Link](https://www.investopedia.com/terms/r/rollingover.asp)
*   **Options Playbook - Diagonal Spread**: [Link](https://www.optionsplaybook.com/option-strategies/diagonal-call-spread/)
*   **Tastytrade - Rolling Logic**: Strategies often focus on rolling for a credit to reduce cost basis.
*   **Juicy Fruit Feature**: `RollService.find_rolls` implemented in `app/services/roll_service.py`.

---


