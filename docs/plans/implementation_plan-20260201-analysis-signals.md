# Implementation Plan - Analysis & Signals (Epic 2)

This plan addresses the "Analysis & Signals" requirements from `docs/features-requirements.md` (Line 120), focusing on the Smart Roll Assistant, Scanners, and bug fixes.

## Goal Description
Implement advanced option analysis tools to help Trader Ken manage existing positions (Smart Roll) and find new opportunities (Scanners). Fix existing bugs in the Opportunity Finder.

## User Review Required
> [!IMPORTANT]
> **Data Source**: The Smart Roll Assistant will rely on **Yahoo Finance** (via `yfinance`) for real-time option chain data, as the current IBKR integration is Flex-Query based (delayed). This means "Real-Time" might have a slight delay or rate limits.

> [!NOTE]
> **Scanner Data**: Scanners will operate on the `stock_data` collection in MongoDB, which is updated by the `StockLiveComparison` job. Ensure the "Live Comparison" job is running frequently for accurate scanner results.

## Proposed Changes

### Backend Components

#### [MODIFY] [app/services/options_analysis.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/options_analysis.py)
- Refactor `calculate_strength` to be cleaner / more weighted.
- Fix logic for "Trend UP" detection (Bug fix).
- Add `analyze_rolls` method (or delegate to new service).

#### [NEW] [app/services/roll_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/roll_service.py)
- **Purpose**: Dedicated service for calculating Smart Roll / Diagonal strategies.
- **Functions**:
    - `get_option_chain(ticker, date)`: Wrapper around `yfinance` ticker options.
    - `find_rolls(symbol, current_strike, current_exp, target_date_range)`:
        - Logic to find "Net Credit" or "Low Cost" rolls.
        - Analyze `Calendar` (Same strike, later date) and `Diagonal` (Different strike, later date).
        - Scoring: Yield, Probability of Profit (delta based), Net Credit.

#### [NEW] [app/services/scanner_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/scanner_service.py)
- **Purpose**: Query engine for `stock_data` collection.
- **Functions**:
    - `run_scanner(criteria: dict)`:
        - Example criteria: `IV_Rank > 50`, `Trend == Up`, `Price < EMA_20`.
    - `scan_momentum_calls()`: Special preset for "Call Buying Opportunities".

#### [MODIFY] [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- Add endpoints:
    - `POST /analysis/roll`: Input {symbol, strike, exp, qty}. Output {recommended_rolls: [...]}.
    - `POST /analysis/scan`: Input {filter_config}. Output {tickers: [...]}.

### Logic corrections
- **Bug Fix**: "Trend UP" but reported incorrectly.
    - Identify source of `one_day` change in `OptionsAnalyzer`.
    - Verify `StockLiveComparison` is populating `1D % Change` correctly (it stores string "1.25%", needs parsing).

## Verification Plan

### Automated Tests
- **Unit Tests**:
    - Create `tests/test_roll_service.py`: Mock `yfinance` response, test roll math (Credit/Debit calculation).
    - Create `tests/test_scanner_service.py`: Insert dummy `stock_data` records, test query logic.
    - Update `tests/test_options_analysis.py`: Verify bug fix for Trend detection.

### Manual Verification
- **Smart Roll**:
    - Pick a known "Underwater" short call from Portfolio.
    - Call `/analysis/roll` endpoint via Swagger UI.
    - Verify it suggests logical rolls (e.g., rolling out in time for a credit).
- **Scanner**:
    - Run the "Live Comparison" job to populate DB.
    - Call `/analysis/scan` with simple criteria.
    - Verify returned tickers match the criteria in MongoDB.
- **Bug Check**:
    - Check the "Alerts" endpoint response for MRVL (or similar) coverage alert.
    - Confirm "Trend UP" message matches actual 1D change.
