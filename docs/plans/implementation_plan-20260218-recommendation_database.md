# Implementation Plan - Recommendation Database

## Goal Description
Implement a local persistent MongoDB database to store all generated recommendations, signals, rolls, and dividend opportunities. This will enable historical analysis and future scoring of recommendations to determine their effectiveness (Truth Engine).
This leverages the existing `JuicyOpportunity` model to store all "Signals", "Smart Rolls", and "Scanned Candidates".

## User Review Required
> [!IMPORTANT]
> - **Unified Model**: We will use the existing `JuicyOpportunity` model (`app/models/opportunity.py`) for all persistence.
> - **Volume Control**: We will only persist the "Top 10" or "High Confidence" signals from each scan to avoid database bloat, as per the user's "Top 10 scored recommendation" request.
> - **Scheduled Scans**: We will add new scheduled jobs to run these scans and persist results automatically after market data updates.

## Proposed Changes

### Models
#### [NO CHANGE] `app/models/opportunity.py`
- The existing `JuicyOpportunity` model is suitable.

### Services
#### [MODIFY] `app/services/roll_service.py`
- Update `analyze_portfolio_rolls`:
    - Add `persist: bool = False` argument.
    - If `persist=True`:
        - Convert the top 10 results (or high score results > 50) into `JuicyOpportunity` objects.
        - Save them via `OpportunityService`.
        - `trigger_source` will be "SmartRoll".
    - This allows the UI to request rolls without flooding the DB, while the scheduler can trigger persistence.

#### [MODIFY] `app/services/scanner_service.py`
- Update `scan_momentum_calls` and `scan_juicy_candidates`:
    - Add `persist: bool = False` argument.
    - If `persist=True`:
        - Convert results into `JuicyOpportunity` objects.
        - Save them via `OpportunityService`.
        - `trigger_source` will be "MomentumScanner" or "JuicyScanner".

#### [MODIFY] `app/services/signal_service.py`
- Add `scan_and_persist_signals(tickers: List[str])`:
    - Iterate through tickers (e.g., from portfolio or watchlist).
    - Generate Kalman/Markov signals.
    - If signal is strong (e.g., Confidence > 80% or specific change in state), persist as `JuicyOpportunity`.
    - `trigger_source` will be "SignalService".
- Note: This new method will be called by the scheduler.

### Scheduler
#### [MODIFY] `app/scheduler/jobs.py`
- Create a new wrapper function `run_recommendation_scans`.
- This job will:
    1. Run `scanner_service.scan_momentum_calls(persist=True)`
    2. Run `scanner_service.scan_juicy_candidates(persist=True)`
    3. Run `roll_service.analyze_portfolio_rolls(persist=True)`
    4. Run `signal_service.scan_and_persist_signals(portfolio_tickers)`
- Schedule this job to run daily (e.g., at 10:15 AM, shortly after the main `stock_live_comparison` job at 10:00 AM which updates market data).
- Also schedule it for Post-Market (e.g., 4:30 PM).

### API
#### [MODIFY] `app/api/routes.py`
- Update `/analysis/rolls` endpoint to accept `persist: bool = False`.
- Update `/analysis/scan` endpoint to accept `persist: bool = False`.
- Useful for manual triggering and testing.

## Verification Plan

### Automated Tests
#### [UPDATE] `tests/test_roll_service.py`
- Mock `OpportunityService`.
- Call `analyze_portfolio_rolls` with `persist=True`.
- Verify `OpportunityService.create_opportunity` was called with expected data.

#### [NEW] `tests/test_persistence_integration.py`
- Integration test that mocks `MongoClient` (or uses test DB).
- Runs `scan_momentum_calls(persist=True)`.
- Verifies that a `JuicyOpportunity` document is inserted into the `opportunities` collection.

### Manual Verification
1. **Trigger Scan via API**:
    - Use Swagger UI to `POST /analysis/scan` with `{"preset": "momentum"}` and (once implemented) `persist=True`.
    - Or stick to the `routes.py` update to default `persist=True` if triggered via a specific "Backfill" endpoint.
2. **Check Database**:
    - Use a python script to query MongoDB: `db.opportunities.find({"trigger_source": "MomentumScanner"}).sort({"timestamp": -1}).limit(1)`
    - Verify the document exists and has fields like `proposal`, `context`, `timestamp`.
3. **Frontend Check**:
    - If the frontend "Opportunities" view pulls from this collection, verify the new items appear there.
