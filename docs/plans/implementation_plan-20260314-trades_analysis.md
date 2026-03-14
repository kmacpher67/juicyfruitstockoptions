# Goal Description

The focus of this plan is to resolve three issues present in the Trades Analysis API (`/api/trades/analysis`):
1. **Performance**: The endpoint takes ~2 seconds to process because it fetches all trades for all time and incurs significant Pydantic serialization overhead (`model_dump` inside the inner loop of `calculate_pnl`), and converts thousands of database documents into models before evaluating the specified timeframe.
2. **Missing Account Information**: The `parse_csv_trades` and `parse_xml_trades` methods in `app/services/ibkr_service.py` forgot to map `account_id` from the raw IBKR row into the MongoDB document. Since the DB doesn't have `account_id` for trades, the API cannot return it to the frontend.
2.1 **ALL imported columns saved**: Saved all the imported scrapped columns into the mongo trades collections. ClientAccountID	Symbol	Description	UnderlyingSecurityID	Strike	ReportDate	Expiry	Buy/Sell	DateTime	Put/Call	TradeDate	SettleDateTarget	TransactionType	Quantity	TradePrice	TradeMoney	NetCash	ClosePrice	Open/CloseIndicator	Notes/Codes	CostBasis	FifoPnlRealized	OrderTime	OpenDateTime	LevelOfDetail	TradeID	MtmPnl	TransactionID	IBExecID	RelatedTransactionID	OrderReference	Model	CurrencyPrimary	AssetClass	SubCategory	Conid	SecurityID	SecurityIDType	CUSIP	ListingExchange	UnderlyingSymbol	UnderlyingListingExchange	Issuer	IssuerCountryCode	Exchange	Proceeds	Taxes	IBCommission	IBCommissionCurrency	OrigTradePrice	OrigTradeDate	OrigTradeID	OrigOrderID	OrigTransactionID	ClearingFirmID	IBOrderID	BrokerageOrderID	HoldingPeriodDateTime	WhenRealized	WhenReopened	OrderType	InitialInvestment	PositionActionID	SerialNumber	CommodityType	AccountAlias
3. **Incorrect Counts**: The `TradeMetrics` count logic incorrectly registers any trade execution with `realized_pl == 0` (which is typically every opening leg of a trade) as an "open trade". This drastically inflates the Open Trades count to equal nearly all opening legs rather than the actual number of open positions.

## User Review Required

- **Data Migration Note**: The fix for missing `account_id` will require the IBKR Flex sync to re-pull trades or a manual sync script to update existing trades in the DB if the user relies on historical trades having an account attached. Historical trades that were already parsed will not magically gain an `Account ID` unless the Flex report re-imports them. (The Upsert logic should fix this on the next 365-day sync).
- **Metric Definitions**: Open Trades will now represent the number of *open underlying positions* (e.g., if you are Long 10 AAPL, that is 1 Open Trade), while Closed Trades will count the number of execution legs that realized a non-zero P&L. Is this semantic alignment with trading terminology correct for you?

## Proposed Changes

---
### app/services/ibkr_service.py
Ensure `account_id` is tracked on all trades imported into the database by extracting `ClientAccountID` or `AccountId` from the CSV row / XML node.

#### [MODIFY] app/services/ibkr_service.py
- Update `parse_csv_trades` around line 343 to add `doc["account_id"] = row.get("ClientAccountID") or row.get("AccountId")`.
- Update `parse_xml_trades` around line 388 to add `doc["account_id"] = data.get("accountId")`.

---
### app/services/trade_analysis.py
Optimize the `calculate_pnl` engine to run on lightweight dictionaries rather than doing full Pydantic model serialization in the core calculation loop. Correct the `calculate_metrics` to ensure accurate aggregate data limits.

#### [MODIFY] app/services/trade_analysis.py
- **Performance**: Inside `calculate_pnl`:
  - Avoid using `analyzed = AnalyzedTrade(**t.model_dump())` per loop iteration.
  - Instead, run the algorithm directly on the dictionary attributes of `t` (`data = t.model_dump(by_alias=False)` one time, or directly accessing variables) and instantiate `AnalyzedTrade(**data)` only at the append stage. (Wait, even faster: convert the whole `raw_trades` parameter dynamically and skip redundant `safe_float` overhead).
- **Counts Correction**: Inside `calculate_metrics`:
  - Set `open_trades = len(open_positions.keys())` since this accurately represents the number of active ticker/symbol positions scaling unrealized P&L.

---
### app/api/trades.py
Optimize the fetching overhead by not constructing 10,000 Pydantic objects for `raw_trades` upfront if possible, or streamlining the load.

#### [MODIFY] app/api/trades.py
- Skip slow `[TradeRecord(**fix_oid(doc)) ...]` instantiation for all historical db trades and dividends, and instead construct the final list natively or just once during `calculate_pnl`.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_api_trades.py` to ensure changes to the `/analysis` endpoint pass cleanly, adding additional assertions for `metrics["open_trades"]` and `account_id`.
- Run `pytest tests/test_portfolio_features.py` to ensure downstream functionality dependent on P&L calculations remains correct.

### Manual Verification
1. Access the frontend app history view (`http://localhost:3000/trades`). 
2. Trigger the sync to update recent trades with AccountIDs.
3. Observe rendering of "Account", and confirm that the loading time of `/api/trades/analysis` when filtering by frame (e.g., `1W`, `1Y`) drops substantially under the current ~2.00s overhead via the browser's Network tab.
4. Verify the top summary boxes accurately reflect current open positions and executed trades within the given time frame.
