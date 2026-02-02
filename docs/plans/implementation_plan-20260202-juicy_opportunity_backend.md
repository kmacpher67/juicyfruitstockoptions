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

## Verification Plan
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
