# Goal Description
Integrate IBKR Dividend Flex Reports into the system to parse, store, and display dividend histories per ticker. This includes updating settings to support the new Flex Query ID, building a parsing pipeline, blending dividend events into Trade History, and factoring them into Portfolio metrics.

## Proposed Changes

---

### Backend: Models and Settings
#### [MODIFY] `app/models/__init__.py`
- Add `query_id_dividends: Optional[str] = None` to the Config/System settings models (e.g., `IBKRConfigUpdate`, `SystemConfig`).

#### [MODIFY] `app/api/routes.py`
- Update `get_ibkr_config` to return `query_id_dividends`.
- Update `update_ibkr_config` logic to accept and save `query_id_dividends`.

---

### Backend: IBKR Data Pipeline
#### [MODIFY] `app/services/ibkr_service.py`
- **Parser**: Implement `parse_csv_dividends(csv_str)` to handle the new Dividend Flex Query (e.g., `Dividend_Report (3).csv` formats).
  - Extract `Symbol`, `PayDate`, `ExDate`, `GrossAmount`, `Code` (PO for Pending, RE for Paid), and `AccountId`.
  - Store parsed records in a new MongoDB collection: `ibkr_dividends`, ensuring idempotent upserts using a composite key (e.g., Symbol + PayDate + ActionID/RowID).
- **Sync**: Inside `run_ibkr_sync()`, add the operational step to fetch and parse the dividend report using the configured `query_id_dividends`.

---

### Backend: Trade History & Portfolio Metrics
#### [MODIFY] `app/api/trades.py`
- Update `get_trades` and `get_trade_analysis` to additionally query the `ibkr_dividends` collection for realized ("RE") dividends.
- Map these dividend records into `TradeRecord` structures (e.g., `buy_sell="DIVIDEND"`, `realized_pnl=NetAmount`, `price=0`, `quantity=0`).
- Merge and sort these with the classic trade records so they appear organically in the Trade History UI chronologically.

#### [MODIFY] `app/services/portfolio_analysis.py` (or relevant core analytics calculation)
- When calculating Total Return and True Yield for a holding, retrieve its total received dividends from `ibkr_dividends`.
- Enhance the holding metric payload to return standard P&L + Dividend Yield accurately.

---

### Frontend: Configuration & Views
#### [MODIFY] `frontend/src/components/SettingsModal.jsx`
- Add a text input for **"Dividends Query ID"** beneath the Trades Query ID field in the IBKR configuration section.
- Bind the input correctly to state and the persistence payload.

#### [MODIFY] `frontend/src/components/TradeHistory.jsx`
- Adjust the grid row rendering or data mapping to gracefully handle rows with `buy_sell === 'DIVIDEND'`. Ensure they visually reflect as non-trade cash events (e.g., styling, or showing the dividend value neatly in the P&L column).

#### [MODIFY] `frontend/src/components/PortfolioGrid.jsx` 
- Utilize the new backend dividend metrics to adjust the display of "Total Return" columns, optionally exposing an exclusive "Divs Earned" stat in the tooltips or popups.

---

## Verification Plan
### Automated Tests
- Execute `pytest` emphasizing `tests/test_ibkr_service.py` and `tests/test_api_trades.py` to assert no breaking changes.
- **New Test**: Implement `tests/test_dividends.py`. Feed a mock `Dividend_Report (3).csv` string to `parse_csv_dividends`. Assert that MongoDB receives the correct distinction between "PO" (accruals) and "RE" (actualized cash).
- Coverage must show new logics covered.

### Manual Verification
1. Start the application locally. Navigate to **Settings > IBKR Integration**.
2. Add `1434041` as the Dividend Query ID and hit **Save**.
3. Trigger a manual IBKR Sync. Verify standard output and database logs to capture `ibkr_dividends`.
4. Navigate to the **Trade History** view. Timeframe filter "All trades". Inspect to see if dividend line items appear for `GOOGL`, `WMT`, etc., representing cash payouts accurately.
5. In **My Portfolio**, verify that the True Yield/Return displays factor in the new historical dividend inputs.
