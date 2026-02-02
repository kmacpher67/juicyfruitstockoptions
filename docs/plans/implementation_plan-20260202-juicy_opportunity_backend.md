# Implementation Plan - Juicy Opportunity Collection Backend

## Goal Description
Implement the backend infrastructure to persist "Juicy Opportunities" as defined in the updated `features-requirements.md`. This involves creating a strongly-typed `JuicyOpportunity` model, setting up a MongoDB collection, and creating a service to handle the creation and lifecycle of these opportunities. We will start by integrating this with the `DividendScanner`.

## User Review Required
> [!NOTE]
> This plan focuses on the *Backend Data Layer* and *Service Layer*. Frontend visualization is out of scope for this specific plan but will build upon this data.

## Proposed Changes

### Backend Models
#### [NEW] [app/models/opportunity.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models/opportunity.py)
- Define `JuicyOpportunity` Pydantic model:
    - `symbol`: str (Ticker)
    - `timestamp`: datetime (Detection time)
    - `trigger_source`: str (e.g., "DividendScanner", "GapScanner")
    - `status`: Enum (DETECTED, TRACKING, CLAOSED, DISCARDED)
    - `context`: Dict (Snapshot of Price, IV, Greeks)
    - `proposal`: Dict (The trade specifics, e.g., "Sell Call $100")
    - `outcome`: Optional[Dict] (P&L, MFE, MAE - populated later)

### Backend Services
#### [NEW] [app/services/opportunity_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/opportunity_service.py)
- `create_opportunity(data: JuicyOpportunity)`:
    - Validate data.
    - Insert into MongoDB `opportunities` collection.
    - Return the created ID.
- `get_opportunities(filter: dict)`:
    - Retrieve opportunities with pagination/filtering.

#### [MODIFY] [app/services/dividend_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/dividend_scanner.py)
- Inject `OpportunityService`.
- When a dividend opportunity is found (and meets criteria), call `opportunity_service.create_opportunity` to persist it.

### Database
- **Collection**: `juicy_fruit.opportunities`
- **Indexes**: `symbol`, `timestamp`, `status`, `trigger_source`.

### Scheduler Implementation
#### [NEW] [app/services/scheduler_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/scheduler_service.py)
- **Library**: `APScheduler` (BackgroundScheduler).
- **Jobs**:
    - `run_dividend_scan`: Runs `DividendScanner.scan()` every 30 mins during market hours (9:30 AM - 4:00 PM ET).
    - `run_pre_market_scan`: Runs at 8:30 AM ET.
    - `run_post_market_scan`: Runs at 5:00 PM ET.
- **Integration**: Initialized in `app/__init__.py` or `main.py` startup event.

### API & UI Updates
#### [MODIFY] [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **New Endpoint**: `GET /api/opportunities`
    - Returns persisted opportunities from MongoDB.
    - Filters: `source`, `status`, `min_score`.
- **Update Endpoint**: `GET /api/analysis/dividend-capture`
    - **Change**: Instead of triggering a live scan, this should now return *recent* results from the DB (via `OpportunityService`).
    - **Legacy Support**: Optional `?force_scan=true` parameter to trigger live scan (async).

#### [MODIFY] [frontend/src/components/DividendScanner.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/DividendScanner.jsx)
- **Logic Change**: Fetch from `/api/opportunities?source=DividendScanner` instead of triggering a long-running scan.
- **UX**: Show "Last Updated" timestamp. Add "Refresh" button (calls `force_scan`).

## Verification Plan
### Automated Tests
- **Unit Tests**:
    - Test `JuicyOpportunity` model validation.
    - Test `OpportunityService` CRUD operations (mocking Mongo).
    - Test `DividendScanner` integration (verify it calls the service).
    - Test `SchedulerService` job registration (mock execution).
- **Integration Tests**:
    - Verify data is actually written to the local MongoDB instance.
    - Verify API returns persisted data.

### Manual Verification
- Run the `DividendScanner` (via API or script).
- Inspect MongoDB (via shell or Compass) to verify `opportunities` documents are created with the correct schema.
- Start the application and verify Scheduler logs indicate jobs are added.
- Check Frontend: "Dividend Capture" list should load instantly from DB.
### Automated Tests
- **Unit Tests**:
    - Test `JuicyOpportunity` model validation.
    - Test `OpportunityService` CRUD operations (mocking Mongo).
    - Test `DividendScanner` integration (verify it calls the service).
- **Integration Tests**:
    - Verify data is actually written to the local MongoDB instance.

### Manual Verification
- Run the `DividendScanner` (via API or script).
- Inspect MongoDB (via shell or Compass) to verify `opportunities` documents are created with the correct schema.
