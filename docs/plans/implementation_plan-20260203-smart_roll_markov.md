# Implementation Plan - Smart Roll & Markov Integration

**Goal**: Implement the "Anti-Gravity" Smart Roll logic (Momentum, Gamma, Reset) and integrate Markov Chain signals to drastically improve the intelligence of roll recommendations and portfolio dashboard analytics.

## User Review Required
> [!IMPORTANT]
> **Markov Dependency**: Requires `markovify` and `pykalman` to be installed. Ensure `pip install pykalman markovify` has been run or added to `requirements.txt`.
> **Scoring Complexity**: The new `score_roll` logic introduces non-linear adjustments (Gamma Penalties, Momentum Triggers). This may drastically change the ranking of rolls compared to the simple "Net Credit" sorting.

## Proposed Changes

### 1. Backend: RollService Upgrade ("Anti-Gravity Logic")
*   **File**: `app/services/roll_service.py`
    *   **[MODIFY]** `score_roll`: Implement the advanced logic defined in `docs/learning/smart-roll-diagonal.md`.
        *   **Momentum Trigger**: Check `1D % Change` vs `DTE`. Bonus for "Up & Out" on Bullish trends.
        *   **Gamma Penalty**: Severe penalty for `DTE < 2` if price is near strike (Pin Risk) unless rolling *out*.
        *   **Reset Protocol**: Detect "Deep ITM" + "Bearish Trend" -> Suggest `BTC` (Close) instead of Roll.
        *   **Signal Integration**: Inject `SignalService` dependency. Add "Markov Probabilities" to the score (e.g., if P(UP) > 60%, prioritize Call Rolls).
        *   **Enriched Data**: Calculate and return `UP Return` (Stock Gain if called away), `UP Yield`, and `Total Yield` (Premium + Stock Gain) for every roll option.

### 2. Backend: Signal Service Integration
*   **File**: `app/api/routes.py`
    *   **[MODIFY]** `/api/analysis/signals/{ticker}`: Ensure it returns data in a format consumable by the frontend Ticker Modal.
*   **File**: `app/services/signal_service.py`
    *   **[MODIFY]** `get_roll_vs_hold_advice`: Refine the boolean logic to return a structured 'Advice Object' (Action: ROLL/HOLD, Confidence: 0-100, Reason: "Markov P(UP) 80%").

### 3. Frontend: Ticker Modal & Analysis
*   **File**: `frontend/src/components/TickerModal.jsx` (or equivalent)
    *   **[MODIFY]** Add "Signal Analysis" section.
        *   Display Kalman Trend ("Above Trend" / "Below Trend").
        *   Display Markov Transition Matrix (Visual or Text: "60% Chance of UP move").
    *   **[MODIFY]** Smart Roll Tab: Show "AI Reasoning" (e.g., "Momentum is Bullish, recommending Roll Up"). Show new Metric columns: `UP Return`, `UP Yield`, `Total Yield`.

### 4. UI Fixes & Enhancements (Frontend Polish)
*   **File**: `frontend/src/components/PortfolioGrid.jsx` & `StockGrid.jsx`
    *   **[FIX] Type Column**: Ensure `secType` or `type` is correctly mapped and displayed for each row.
    *   **[FIX] XDTE Width**: Force XDTE widget containers to use full available width (prevent 1/2 width rendering).
*   **File**: `frontend/src/components/TradeHistory.jsx`
    *   **[FIX] Option Display**: Add logic to distinguish OPT vs STK. Show explicit `BUY/SELL` and `OPEN/CLOSE` tags. 
    *   **[FIX] Yield Display**: If trade is a Close, calculate and show realized yield.
*   **File**: `app/services/expiration_scanner.py` or Frontend Utility
    *   **[FIX] DTE Calculation**: Debug "2D vs 4D" discrepancy. Ensure standardized `(Expiry - Now).days` calculation is consistent across Backend and Frontend (See `docs/learning/dte-calculation-standards.md`).

### 5. Database / Persistence
*   **File**: `app/models/opportunity.py` (if exists) or new Schema.
    *   **[NEW/MODIFY]**: Store generated Signals with the Opportunity for backtesting "Truth Engine" later.

## Verification Plan

### Automated Tests
*   `pytest tests/test_roll_service.py`: Verify `score_roll` prioritizes "Smart Rolls" over distinct bad ones. 
    *   *Case*: Bullish Momentum + DTE 2 -> Roll Up Score > Hold Score.
    *   *Case*: Bearish + Deep ITM -> BTC Recommendation.
*   `pytest tests/test_signal_service.py`: Verify Markov transition matrix generation on mock data.

### Manual Verification
1.  **Browser**: Open Ticker Modal for a known volatile stock (e.g., TSLA/NVDA).
2.  **Verify**: "Signal Analysis" section appears.
3.  **Verify**: "Smart Roll" suggestions include Reasoning text (e.g., "Gamma Risk Detected").
