# Goal Description
Fix the Dividend Scanner bug reported by the user:
1.  **Scheduler Bug**: The scheduler attempts to call `scanner.generate_dividend_calendar()`, which does not exist. It should call `generate_corporate_events_calendar()`.
2.  **Lookahead Logic**: The scanner currently looks for opportunities 2-14 days out. This misses opportunities for "tomorrow" (1 day out) and "today" (if checking early). The user asked "How far out does it look?". We will expand this window to 0-30 days to be more inclusive and useful.

## User Review Required
> [!IMPORTANT]
> **Lookahead Window Change**: Changing the window from `2-14 days` to `0-30 days` will increase the number of opportunities found. This is intentional to cover "imminent" dividends (tomorrow) and further out planning.

## Proposed Changes

### Backend Services

#### [MODIFY] [dividend_scanner.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/dividend_scanner.py)
- Update `scan_dividend_capture_opportunities` method:
    - Change lookahead logic from `if 2 <= days_to_ex <= 14:` to `if 0 <= days_to_ex <= 30:`. 
    - This allows catching dividends happening *today* (0), *tomorrow* (1), and up to a month out.

#### [MODIFY] [jobs.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/scheduler/jobs.py)
- Fix typo in `run_dividend_calendar_job`.
    - Change `scanner.generate_dividend_calendar()` to `scanner.generate_corporate_events_calendar()`.

## Verification Plan

### Automated Tests
- Run the reproduction test `tests/test_bug_repro.py` (updated to mock dependencies correctly).
- Run existing tests: `pytest tests/test_dividend_features.py`
- Run all tests: `pytest`

### Manual Verification
- Review the logs after restarting the application to verify the scheduler starts without error.
- Trigger the scan manually via API (if endpoint exists) or wait for scheduler.
- Verify "Corporate Events" calendar is generated in `xdivs/` directory.
