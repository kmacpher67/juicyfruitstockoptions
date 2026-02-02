# Walkthrough - Greeks Integration

## Overview
We have successfully integrated the calculation of Option Greeks (Delta, Gamma, Theta) into the backend services. Since our primary data source (`yfinance`) does not provide these metrics, we implemented a custom calculation engine using the Black-Scholes model via `py_vollib_vectorized`.

## Changes
1.  **Dependencies**: Added `py_vollib_vectorized` to `requirements.txt`.
2.  **Calculator Utility**: Created `app/utils/greeks_calculator.py` which takes a DataFrame of option data (Strike, Time, IV) and returns it enriched with Delta, Gamma, and Theta.
3.  **Service Integration**: Updated `RollService.find_rolls` to utilize the calculator. Now, every "Smart Roll" opportunity returned by the API includes these Greek metrics.
4.  **Data Model**: Updated `TradeRecord` in `app/models.py` to support storage of these metrics.

## Verification Results

### Automated Tests
We added unit tests in `tests/test_greeks_calculator.py` and updated `tests/test_roll_service.py`.

```bash
$ pytest tests/test_greeks_calculator.py tests/test_roll_service.py
============================= test session starts ==============================
...
tests/test_greeks_calculator.py ....                                     [ 80%]
tests/test_roll_service.py .                                             [100%]

============================== 5 passed in 2.12s ===============================
```

### Manual Verification (Simulated)
The integration was verified by running `tests/test_roll_service.py` which simulates the full flow:
1.  Mock `yfinance` returns an option chain with IV but no Greeks.
2.  `RollService` invokes `GreeksCalculator`.
3.  The result (`cal_roll`) contains `delta`, `gamma`, and `theta` keys.

```python
# From tests/test_roll_service.py
assert "delta" in cal_roll
assert "gamma" in cal_roll
assert "theta" in cal_roll
```

## Next Steps
-   **Smart Roll Logic**: Update the `score_roll` algorithm to uses these new metrics (e.g., penalize high Gamma, target Delta neutrality).
-   **UI Display**: Update the Frontend to display these Greeks in the "Smart Roll" suggestions table.
