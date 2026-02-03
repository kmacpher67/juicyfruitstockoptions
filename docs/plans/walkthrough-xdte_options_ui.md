# Walkthrough - X-DTE Options UI & Auto-Roll

## Completed Work
We have implemented the UI and integration for the "Options Due in X Days" signal and "Auto-Roll Evaluation".

### Components Created/Modified
1.  **[NEW] `frontend/src/components/RollAnalysisModal.jsx`**: 
    - A dedicated modal to visualize roll opportunities for a specific position.
    - Fetches data from `POST /api/analysis/roll`.
    - Displays current position stats, cost to close, and a list of recommended rolls with scores.

2.  **[MODIFY] `frontend/src/components/AlertsDashboard.jsx`**:
    - Now fetches opportunities from `GET /api/opportunities?source=ExpirationScanner`.
    - Displays a new section for Expiring Options (blue/indigo style).
    - Added "Roll?" button to trigger the analysis modal.

3.  **[MODIFY] `frontend/src/components/Dashboard.jsx`**:
    - Integrated `RollAnalysisModal`.
    - Manages state for `selectedRollOpportunity`.

4.  **[NEW] `tests/test_api_roll_analysis.py`**:
    - Integration test verifying the `POST /api/analysis/roll` endpoint correctly accepts parameters and calls `RollService`.

### Verification Results
- **Unit Tests**: `tests/test_roll_service.py` passed.
- **Integration Tests**: `tests/test_api_roll_analysis.py` passed (verified API argument handling).


## Command Line Verification

To verify the backend logic and database state without using the UI, you can use the provided scripts.

### 1. Install Dependencies
Ensure your local environment has the necessary packages.
```bash
pip install pydantic-settings httpx py_vollib_vectorized
```
*Note: These are required for the standalone scripts to run independently of the full app container.*

### 2. Run Verification Scripts
You must provide the `MONGO_URI` environment variable if running locally against the Docker Mongo instance.

**Step A: Trigger the Scanner**
This will verify that the `ExpirationScanner` can find potential rolls and save them to the database.
```bash
MONGO_URI="mongodb://admin:admin123@localhost:27017/?authSource=admin" python run_scanner.py
```

**Step B: Verify Database State**
This script checks if the X-DTE logic correctly identified positions for a specific account (e.g., U110638).
```bash
MONGO_URI="mongodb://admin:admin123@localhost:27017/?authSource=admin" python verify_xdte.py
```

### 3. Running Unit Tests
If you wish to run the unit tests locally (e.g., `tests/test_api_roll_analysis.py`), use the following command to ensure the correct environment variables and paths are loaded:
```bash
python -m pytest tests/test_api_roll_analysis.py
```
*Note: Using bare `pytest` might fail if your environment paths are not perfectly aligned. `python -m pytest` is safer.*

## How to Verify Manually (UI)
1.  **Check Dashboard**:
    - Open the Dashboard.
    - Look for the **Expiring Options** cards (Indigo colored) in the Alerts area.
    - Ensure the DTE and Symbol match.

2.  **Test Roll Analysis**:
    - Click the **"Roll?"** button on an expiration card.
    - The **Smart Roll Analysis** modal should open.
    - It should show "Analyzing..." then display a list of roll candidates.
    - Verify that `Net Credit` and `Score` are displayed.
    - Click "Select" to confirm the action button works (currently logs to console).

## Next Steps
- Implement "Execute Roll" button functionality (integration with IBKR Order Placement).
- Refine "Score" logic based on real-world feedback.
