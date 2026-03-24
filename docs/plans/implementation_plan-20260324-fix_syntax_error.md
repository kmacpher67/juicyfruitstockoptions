# Goal Description
The file `tests/test_ibkr_service_trades.py` contains a `SyntaxError` due to unnecessary backslashes before triple quotes. This plan outlines the steps to fix it and verify the changes.

## Proposed Changes
### Backend / Tests
#### [MODIFY] [test_ibkr_service_trades.py](file:///home/kenmac/personal/juicyfruitstockoptions/tests/test_ibkr_service_trades.py)
* Remove the backslashes `\` from lines 5 and 7:
  - Line 5: `CSV_TRADES = \"\"\"...` -> `CSV_TRADES = """...`
  - Line 7: `\"\"\"` -> `"""`

## Verification Plan
### Automated Tests
* Run `pytest tests/test_ibkr_service_trades.py` to ensure the syntax error is gone and the tests pass.
* Run all tests `pytest` to ensure no regressions.
