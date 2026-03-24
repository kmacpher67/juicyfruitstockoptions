# Implementation Plan: Set Default Trade History View to YTD

The goal is to change the default time range for the trade history view from "ALL" to "YTD" (Year To Date) to provide more relevant data upon initial load.

## User Review Required

- None. This is a simple default value change as requested in the documentation.

## Proposed Changes

### Frontend

#### [MODIFY] [TradeHistory.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TradeHistory.jsx)
- Change the initial state of `timeRange` from `'ALL'` to `'YTD'`.

### Backend (if applicable)

#### [MODIFY] [trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/trades.py)
- Ensure the API handles empty dates correctly or set a default if needed (though the frontend already sends dates if not 'ALL').

### Documentation

#### [MODIFY] [features-requirements.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/features-requirements.md)
- Mark the task as completed.

## Verification Plan

### Automated Tests
- Run `pytest` to ensure no regressions in trade analysis.

### Manual Verification
- Open the trade history view in the browser and verify that "YTD" is selected by default and data is loaded for the current year.
