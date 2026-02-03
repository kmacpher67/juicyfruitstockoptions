# Implementation Plan - Markov Chains & Kalman Filters

## Goal Description
Implement a new **Signal Generation Service** that leverages **Kalman Filters** for trend/mean reversion analysis and **Markov Chains** for probabilistic state transition modeling. This service will provide data to support "Roll vs. Hold" decisions and general signal analysis for the portfolio.

## User Review Required
> [!NOTE]
> This plan introduces new dependencies: `pykalman` and `markovify`.
> The "Roll vs Hold" logic will be probabilistic (based on historical transitions), not deterministic.

## Proposed Changes

### Dependencies
#### [MODIFY] [requirements.txt](file:///home/kenmac/personal/juicyfruitstockoptions/requirements.txt)
- Added `markovify` and `pykalman`. (Already tentatively added in research phase, will confirm).

### Backend
#### [NEW] [app/services/signal_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/signal_service.py)
- `class SignalService`:
    - `get_kalman_signal(ticker_data)`: Returns calculated Kalman Mean and Signal (Above/Below Trend).
    - `get_markov_probabilities(ticker_data)`: Returns transition matrix and next-state probabilities.
    - `get_roll_vs_hold_advice(ticker, option_details)`: Uses Markov simulation to compare EV of holding vs rolling (MVP: Returns probability of underlying price improvement).

#### [MODIFY] [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- Add new router or endpoints for `/api/analysis/signals/{ticker}`.
- Integrate `SignalService` into existing analysis routes if appropriate.

#### [MODIFY] [app/services/option_analyzer.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/option_analyzer.py)
- Update `RollService` or `SmartRoll` logic to include a "Signal Score" or "Probabilistic Outlook" from `SignalService`.

### Frontend (Future/Follow-up)
- Update `TickerModal` to display signal data.
- This plan focuses on Backend foundation.

## Verification Plan

### Automated Tests
- **Unit Tests**: Create `tests/test_signal_service.py`.
    - Test `get_kalman_signal` with mock data (known trend).
    - Test `get_markov_probabilities` with mock data (known pattern).
    - Command: `pytest tests/test_signal_service.py`
- **Integration Tests**: Verify API endpoint returns 200 and valid JSON structure.
    - Command: `pytest tests/test_api_routes.py` (or new test file).

### Manual Verification
- **Prototype Check**: Run `prototypes/markov_kalman_test.py` to visually confirm math is sound (Already done).
- **API Check**: curl the new endpoint to see generated signals for a live ticker (e.g., SPY).
