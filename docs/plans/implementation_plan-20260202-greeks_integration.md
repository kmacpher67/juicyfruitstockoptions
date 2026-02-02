# Implementation Plan - Greeks Integration

## Goal Description
Integrate Option Greeks (Delta, Gamma, Theta) calculation into the backend services. Since the public data source (`yfinance`) does not provide these metrics, we will implement a calculation engine using the Black-Scholes model via `py_vollib_vectorized`. This will support the "Smart Roll" feature by allowing risk-based scoring (Gamma Risk, Delta Neutrality).

## User Review Required
> [!NOTE]
> This plan introduces a new heavy dependency `py_vollib_vectorized` (based on `scipy`/`numpy`). Ensure the environment allows installing these scientific packages.

## Proposed Changes

### Infrastructure
#### [MODIFY] [requirements.txt](file:///home/kenmac/personal/juicyfruitstockoptions/requirements.txt)
- **Add Dependency**: `py_vollib_vectorized>=0.1.0` (and `scikit-learn` if needed, but likely just `pandas`/`numpy` which are present).

### Shared Utilities
#### [NEW] [app/utils/greeks_calculator.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/utils/greeks_calculator.py)
- **Class**: `GreeksCalculator`
- **Method**: `calculate_dataframe(df: pd.DataFrame, underlying_price: float, risk_free_rate: float = 0.045) -> pd.DataFrame`
    - Accepts a DataFrame with columns: `strike`, `time_to_expiry_years`, `impliedVolatility`, `type` ('c' or 'p').
    - Returns DataFrame with added columns: `delta`, `gamma`, `theta`.
    - Handles exceptions (e.g., IV=0, invalid inputs) gracefully (returns slightly invalid or 0 greeks rather than crashing).

### Domain Layer (Services)
#### [MODIFY] [app/services/roll_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/roll_service.py)
- **Update Method**: `find_rolls`
    - **Step 1**: After fetching option chain from `yfinance`, calculate `time_to_expiry_years`.
    - **Step 2**: Call `GreeksCalculator.calculate_dataframe`.
    - **Step 3**: Include `delta`, `gamma`, `theta` in the returned dictionary list for each roll candidate.

### Data Models
#### [MODIFY] [app/models.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models.py)
- **Update Class**: `TradeRecord` (and potentially `OptionContract` if it exists)
    - Add optional fields: `delta: Optional[float]`, `gamma: Optional[float]`, `theta: Optional[float]`.

## Verification Plan

### Automated Tests
- **New Test File**: `tests/test_greeks_calculator.py`
    - `test_calculate_call_greeks`: specific known inputs (e.g. ATM call) should return expected Delta (~0.5).
    - `test_zero_volatility`: Ensure it handles bad data without crashing.
- **Update Test**: `tests/test_roll_service.py`
    - Verify `find_rolls` output now contains `delta`, `gamma`, `theta` keys.

### Manual Verification
1.  **Run Analysis**: Hit the `Smart Roll` endpoint (or call service in shell).
2.  **Inspect Logs**: Check `app.utils.greeks_calculator` logs for successful batch processing.
3.  **Validate Output**: Check a known option (e.g., deep ITM call) has Delta close to 1.0.
