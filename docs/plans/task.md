# Task List: Price Action Features

- [x] **Backend: Implementation (TDD)**
    - [x] Create `tests/test_price_action.py` (Red).
    - [x] Implement `find_pivots` (ZigZag n=5).
    - [x] Implement `identify_structure` (HH, HL, etc.).
    - [x] Implement `detect_bos` (Body Close).
    - [x] Implement `detect_fvg` (Imbalance).
    - [x] Implement `find_order_blocks` (Validated).
    - [x] Create `app/services/price_action_service.py` (Green).

- [x] **Backend: Integration**
    - [x] Update `stock_live_comparison.py` to call `PriceActionService`.
    - [x] Update field definitions in `fetch_ticker_record` to include new fields.
    - [x] Verify `app/api/routes.py` passes data through (Data flows implicitly).

- [x] **Frontend: Visualization**
    - [x] Update `TickerModal.jsx` to add "Price Action" tab.
    - [x] Render Trend Direction.
    - [x] Render List of Structure Points.
    - [x] Render Order Blocks/FVGs.

- [x] **Verification**
    - [x] Run `pytest tests/test_price_action.py`.
    - [ ] Manual Check via Dashboard (User to perform).
    - [x] Fix Regression: `pytest` failures in legacy tests passed.
