# Price Action & Market Structure Algorithms

This document defines the algorithmic approach for identifying "Price Action" concepts such as Market Structure (HH, HL), Break of Structure (BOS), and Order Blocks. These definitions will guide the implementation of the `PriceActionService`.

## 1. Market Structure (HH, HL, LH, LL)

**Concept**: Identifying the "Trend" enables us to know if the market is Bullish (making Higher Highs and Higher Lows) or Bearish (Lower Lows and Lower Highs).

**Algorithm (ZigZag / Pivot Points)**:
To identify swing points, we will use a **window-based pivot detection**:
- A candle is a **Swing High** if its High is greater than the Highs of the `n` candles before it and `n` candles after it.
- A candle is a **Swing Low** if its Low is lower than the Lows of the `n` candles before it and `n` candles after it.

*Proposed Default*: `n=3` (looks at 3 candles left, 3 candles right).

**Classification**:
- **Higher High (HH)**: A Swing High > Previous Swing High.
- **Lower High (LH)**: A Swing High < Previous Swing High.
- **Higher Low (HL)**: A Swing Low > Previous Swing Low.
- **Lower Low (LL)**: A Swing Low < Previous Swing Low.

## 2. Break of Structure (BOS)

**Concept**: A continuation of the trend.
- **Bullish BOS**: When price closes above the previous **Highest High** (in a defined range or the most recent Swing High).
- **Bearish BOS**: When price closes below the previous **Lowest Low**.

**Algorithm**:
1. Identify the most recent confirmed Swing High/Low.
2. Monitor strictly for a **Candle Close** beyond this level.
3. Mark the line as "Broken" (BOS). The trend continues.

## 3. Order Blocks (OB)

**Concept**: Areas where institutional orders originated. Often defined as the "last opposite candle before a strong move that broke structure."

**Algorithm**:
1. Identify a **BOS** event.
2. For a **Bullish BOS**: Look back from the breakout point. Find the **last bearish candle** (Red candle) before the impulsive move up started.
    - **Zone**: The entire range of that bearish candle (High to Low).
3. For a **Bearish BOS**: Look back for the **last bullish candle** (Green candle) before the drop.
    - **Zone**: High to Low of that candle.

## 4. Supply & Demand Zones

**Concept**: Similar to Order Blocks but broader. Often defined by "explosive moves" leaving "imbalance" (Fair Value Gaps).

**Algorithm (Simplified for V1)**:
- We will treat **Unmitigated Order Blocks** as our primary Supply/Demand zones.
- **Mitigation**: If price returns to the zone and touches it, the zone is considered "tested" or "mitigated".

## 5. Learning & Feedback Questions
> [!NOTE]
> Questions for Trader Ken:
> 1.  **Pivot Sensitivity**: Is a 3-candle lookback (`n=3`) sufficient for Daily charts? Or should we use a percentage threshold (e.g., price moves 5%)?
> 2.  **BOS Definition**: Do you require a **Body Close** to confirm BOS, or is a **Wick Break** sufficient? (Defaulting to Body Close for higher reliability).
> 3.  **Data Granularity**: Are you trading these signals on the **Daily** chart (which `yfinance` provides easily) or do you need **Intraday** (1h, 15m) structure? (V1 will use Daily).
> 4.  **Imbalance**: Should we explicitly detect **Fair Value Gaps (FVG)** alongside Order Blocks?

Asked Gemini in a different window: 

To implement the `PriceActionService` effectively based on the provided technical document, we can break down the recommended actions, benefits, and strategic employment of these algorithms.

---

## Recommended Actions for Implementation

Based on the feedback questions in your document, here are the recommended paths forward:

### 1. Address the Pivot Sensitivity ()

* **Recommendation**: Implement a **dynamic lookback** or a **percentage filter**.
* **Why**: On a Daily chart, a 3-candle window is very "noisy" and may identify minor fluctuations as major trend changes.
* **Action**: Use  for Daily charts or add a requirement that the price must move at least  (e.g., 2–3%) away from the pivot to confirm it as a valid Swing High/Low.

### 2. Confirm BOS Criteria (Body Close vs. Wick)

* **Recommendation**: Default to **Body Close** for Break of Structure (BOS).
* **Why**: Wick breaks often represent "liquidity grabs" or "fakeouts" where price spikes beyond a level but fails to sustain momentum. A body close confirms institutional commitment to the new direction.

### 3. Integrate Fair Value Gaps (FVG)

* **Recommendation**: Explicitly add **FVG detection** to the Order Block (OB) algorithm.
* **Why**: An Order Block is significantly high-probability if it is followed by an "imbalance" or FVG. This proves the move was "explosive."
* **Action**: Code a check to see if the second candle after the OB leaves a gap between the first candle's wick and the third candle's wick.

---

## Benefits of Using These Algorithms

Using an algorithmic approach to Price Action (often called "SMC" or Smart Money Concepts) provides several advantages over manual charting:

* **Objectivity**: It removes the "trader's bias." The algorithm will define a Higher High (HH) the same way every time, preventing you from "seeing what you want to see" during a live trade.
* **Scalability**: While a human can track 3–5 charts for structure, the `PriceActionService` can scan hundreds of tickers across multiple timeframes instantly to find unmitigated Order Blocks.
* **Backtesting Precision**: You can mathematically prove the win rate of a "Bullish BOS + Order Block" setup over 10 years of data, which is nearly impossible to do accurately by hand.

---

## When and How to Employ These Algorithms

These algorithms are most effective when used in a "top-down" sequence:

### The Workflow

1. **Trend Identification (The "When")**: Run the **Market Structure** algorithm first. Only look for Bullish Order Blocks if the structure is confirmed as HH/HL (Bullish).
2. **Zone Mapping (The "Where")**: Once a **BOS** is detected, the algorithm should automatically draw the **Order Block** zone.
3. **Trade Execution (The "How")**:
* **Entry**: Set limit orders at the "Mean Threshold" (50% mark) or the "Open" of the Order Block.
* **Invalidation**: The algorithm should flag the zone as "invalid" if the price closes on the opposite side of the OB (Mitigation/Breach).



### Strategic Employment

* **Context Matters**: These algos work best in **trending markets**. In a "Chop" or sideways market, the ZigZag algorithm will trigger constant LH/HL flips, leading to "whipsaw" losses.
* **Timeframe Alignment**: Use the algorithm to find Daily structure, then drop to a lower timeframe (like 1h) to find an Order Block that aligns with that Daily trend.

