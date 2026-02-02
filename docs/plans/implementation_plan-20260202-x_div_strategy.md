# Implementation Plan - X-DIV Strategy Integration

## Goal
Integrate "X-DIV" (Ex-Dividend) logic into the Smart Roll Assistant. The primary goal is to **protect** the user from Early Assignment Risk on short call positions by factoring the Ex-Dividend Date and Dividend Amount into the roll scoring algorithm.

## User Review Required
> [!IMPORTANT]
> **Data Availability**: We rely on `yfinance` for dividend data. If `yfinance` data is missing or delayed, the risk calculation may fail. We should implement a "Data Unavailable" warning.

## Proposed Changes

### Backend

#### [MODIFY] [requirements.txt](file:///home/kenmac/personal/juicyfruitstockoptions/requirements.txt)
- Add `ics` library for generating calendar files.

#### [MODIFY] [roll_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/roll_service.py)
- **Update Method**: `find_rolls`
    - Fetch Ex-Dividend Date and Dividend Rate from `ticker.info` or `ticker.dividends`.
    - Pass this data to `score_roll`.
- **Update Method**: `score_roll`
    - **New Heuristic**: "Dividend Assignment Risk"
        - IF `Short Call is ITM` AND `Ex-Div Date <= New Expiry` AND `New Extrinsic Value < Dividend Amount`:
            - **Penalty**: -50 Score (Danger).
        - IF `New Extrinsic Value > Dividend Amount * 1.5`:
            - **Bonus**: +10 Score (Safe Buffer).

#### [NEW] [app/services/dividend_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/dividend_scanner.py)
- **New Service**: `DividendScanner`
- **Method**: `scan_dividend_capture_opportunities(tickers)`
    - **Logic**:
        - Find stocks with Ex-Div date in 3-10 days.
        - Yield > 2% (Annualized).
        - Liquid Options.
        - **Strategy**: Suggest "Buy-Write" (Buy Stock + Sell ITM Call).
        - **Score**: Based on Downside Protection (Call Premium) vs Dividend Amount.

#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **New Endpoint**: `GET /api/analysis/dividend-capture`
    - Calls `DividendScanner.scan_dividend_capture_opportunities`.
- **New Endpoint**: `GET /api/calendar/dividends.ics`
    - **Purpose**: Export Ex-Div dates for Portfolio Tickers.
    - **Logic**:
        - Fetch all portfolio tickers.
        - Get Ex-Div dates.
        - Generate `.ics` file with events: "Ex-Div: [Ticker] ($[Amount])".
    - **Response**: File download (`text/calendar`).

#### [MODIFY] [greeks_calculator.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/utils/greeks_calculator.py)
- Ensure we are correctly calculating Theoretical Price/Extrinsic Value.

## Verification Plan

### Automated Tests
- **Run Unit Tests**: `pytest tests/test_smart_roll.py`
    - **New Test**: `test_score_roll_dividend_risk` (Logic verification).
- **New Test File**: `tests/test_dividend_features.py`
    - `test_ics_generation`: Verify `.ics` content format.
    - `test_dividend_capture_logic`: Verify logic finds upcoming ex-divs.

### Manual Verification
1.  **Risk**: Check `score` changes for ITM calls near Ex-Div.
2.  **Capture**: Hit `/api/analysis/dividend-capture` and check for results.
3.  **Calendar**: Download `/api/calendar/dividends.ics` and open in Google Calendar/Outlook.
