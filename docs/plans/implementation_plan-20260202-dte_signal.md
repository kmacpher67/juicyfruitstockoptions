# Implementation Plan - Options Due Signal (DTE < 7)

## Goal Description
Implement a backend signal that automatically scans the user's portfolio for options expiring within 7 days (DTE < 7). These positions should be flagged as `JuicyOpportunity` items with status `DETECTED` to alert the user to take action (Close, Roll, or Assign).

## User Review Required
> [!NOTE]
> This feature reuses the existing `JuicyOpportunity` persistence model but adds a new `trigger_source="ExpirationScanner"`.

## Proposed Changes

### Backend Services
#### [NEW] [app/services/expiration_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/expiration_scanner.py)
- **Class**: `ExpirationScanner`
- **Method**: `scan_portfolio_expirations(days_threshold=7)`
    - Fetch latest portfolio holdings from MongoDB.
    - Filter for Options (`secType="OPT"` or `FOP`).
    - Calculate DTE.
    - If DTE <= threshold:
        - Check if `JuicyOpportunity` already exists for this symbol/expiry to avoid duplicates? (Maybe check `DETECTED` status for today).
        - Create `JuicyOpportunity`:
            - `trigger_source`: "ExpirationScanner"
            - `proposal`: { "action": "Review", "details": "Expiring in X days" }
        - Persist via `OpportunityService`.

### Scheduler
#### [MODIFY] [app/scheduler/jobs.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/scheduler/jobs.py)
- Add job to run `ExpirationScanner` daily at market open (9:30 AM).

## Verification Plan
### Automated Tests
- **Unit Loop**: Mock Portfolio Data with various expiry dates. Verify only those < 7 days trigger an opportunity creation.
### Manual Verification
- Trigger scan manually via script/API.
- Verify "Options Due" appear in the Opportunity collection.
