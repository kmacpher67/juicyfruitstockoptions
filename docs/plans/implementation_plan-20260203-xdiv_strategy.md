# Implementation Plan - X-DIV Strategy

**Goal**: Implement the X-DIV (Dividend Capture) strategy features, including persistent ICS calendar generation, and refactor the UI to use a standardized 3-step flow (Widget -> List -> Analysis), improving consistency with the Smart Roll interface.

## User Review Required
> [!NOTE]
> **UI Refactor**: The flow is now:
> 1. **Dashboard Widget**: Compact summary (e.g., "5 Opps").
> 2. **List Modal**: Intermediate screen listing all opportunities by Date/Account/Ticker.
> 3. **Analysis Modal**: Clicking an item in the list opens the detailed Analysis view for that specific ticker.
> 
> **Persistence**: A new `xdivs/` directory will be created in the workspace root to store daily `.ics` files.

## Proposed Changes

### 1. Backend: Calendar Persistence
*   **Directory**: Create `xdivs/` in the project root.
*   **File**: `app/api/routes.py`
    *   **[MODIFY]** `get_dividend_calendar` endpoint (`/api/calendar/dividends.ics`):
        *   Generate filename: `xdivs/dividends_YYYY-MM-DD.ics`.
        *   Check if file exists:
            *   **If yes**: Read and return file content (Cache Hit).
            *   **If no**: Generate ICS content (using `ics` library as logic exists), save to file, then return content.
        *   Ensure the `xdivs` directory exists (create if not).

### 2. Frontend: Analysis Modal (Detail View)
*   **File**: `frontend/src/components/DividendAnalysisModal.jsx` (New)
    *   **[NEW]** Create a `DividendAnalysisModal` that mimics the layout of `RollAnalysisModal` but triggers for a *single* selected opportunity.
    *   **Features**:
        *   Header with Context (Dividend Capture).
        *   Details: Ex-Date, Dividend Amount, Annual Yield, Score.
        *   "Select" button to log action.

### 3. Frontend: Intermediate List Modal
*   **File**: `frontend/src/components/DividendListModal.jsx` (New)
    *   **[NEW]** Create a modal to list all available opportunities.
    *   **Layout**:
        *   Table/Grid listing: Date, Ticker, Dividend, Yield, Score.
        *   **Interaction**: Clicking a row opens `DividendAnalysisModal` for that item.

### 4. Frontend: Dashboard Integration
*   **File**: `frontend/src/components/DividendScanner.jsx`
    *   **[MODIFY]** Refactor to be a simple "Widget/Button".
    *   **[MODIFY]** On click -> Open `DividendListModal`.
    *   **[MODIFY]** Manage state for the nested modals (Scanner -> List -> Analysis).

### 5. Frontend: Dashboard Layout
*   **File**: `frontend/src/components/Dashboard.jsx`
    *   **[MODIFY]** Update usage of `DividendScanner`.
    *   **[MODIFY]** Ensure modals are properly anchored (or use a global modal context if available, otherwise nest or lift state).

## Verification Plan

### Automated Tests
*   **Backend**: `tests/test_calendar.py` (New)
    *   Test `get_dividend_calendar`:
        *   Call endpoint.
        *   Verify `xdivs/` folder contains today's file.
        *   Call endpoint again, verify file timestamp implies no re-generation.
        *   Verify file content is valid ICS.

### Manual Verification
1.  **Backend Persistence**:
    *   Trigger calendar download.
    *   Run `ls -l xdivs/` to confirm file creation.
2.  **UI Flow**:
    *   **Step 1**: Click "Dividend Capture" widget on Dashboard.
    *   **Step 2**: Verify `DividendListModal` opens with a table of opportunities.
    *   **Step 3**: Click a row (e.g., "MSFT").
    *   **Step 4**: Verify `DividendAnalysisModal` opens with details for MSFT.
    *   **Step 5**: Click "Select" and verify success toast.
