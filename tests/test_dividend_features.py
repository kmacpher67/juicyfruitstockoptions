import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.roll_service import RollService
# Will import DividendScanner and routes later when implemented

# --- Helper ---
def create_roll(strike=100.0, net_credit=0.10, days=7, delta=0.50, call_price=2.00, underlying_price=105.0):
    # Intrinsic = 5.0. Price = 2.0? Impossible if ITM.
    # Let's make it realistic. ITM Call.
    # Strike 100, Stock 105. Intrinsic = 5.0. Option Price should be > 5.0.
    # Say Price = 5.50. Extrinsic = 0.50.
    return {
        "strike": strike,
        "net_credit": net_credit,
        "days_extended": days,
        "delta": delta,
        "bid": call_price, 
        "expiration": (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d"),
        "roll_type": "Roll Out"
    }

def create_market(price=105.0):
    return {"current_price": price, "one_day_change": 0.0}

def create_current(strike=100.0):
    return {"strike": strike, "average_cost": 2.0}

# --- Tests ---

def test_score_roll_dividend_risk_penalty():
    service = RollService()
    
    # Scenario: Short Call ITM.
    # Stock 105, Strike 100. Intrinsic = 5.0.
    # Ex-Div Date is Tomorrow (Risk!). Dividend is $1.00.
    # Case A: Option Price $5.20. Extrinsic = 0.20.
    # Risk: Dividend (1.00) > Extrinsic (0.20). Early Assignment is certain.
    
    roll = create_roll(strike=100, call_price=5.20, underlying_price=105.0)
    # We need to pass dividend info to score_roll? 
    # The plan says "Update Method: score_roll ... New Heuristic".
    # Implementation: score_roll(roll_data, current_pos, market_data, dividend_info=None)
    
    dividend_info = {
        "ex_date": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"), # imminent
        "amount": 1.00
    }
    
    # We need to pass this new arg.
    # Assuming code will be: score_roll(..., dividend_info)
    score, _ = service.score_roll(roll, create_current(), create_market(), dividend_info=dividend_info)
    
    # Expect Penalty. Base 50. 
    # Credit (+0.10) ? Let's say +20. 
    # Div Risk Penalty (-50).
    # Result should be low.
    assert score <= 30
    
def test_score_roll_dividend_safety_buffer():
    service = RollService()
    
    # Scenario: Short Call ITM.
    # Stock 105, Strike 100. Intrinsic = 5.0.
    # Ex-Div Date is Tomorrow. Dividend is $1.00.
    # Case B: Option Price $7.00. Extrinsic = 2.00.
    # Safety: Extrinsic (2.00) > Dividend (1.00). Safe.
    
    roll = create_roll(strike=100, call_price=7.00, underlying_price=105.0)
    dividend_info = {
        "ex_date": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "amount": 1.00
    }
    
    score, _ = service.score_roll(roll, create_current(), create_market(), dividend_info=dividend_info)
    
    # Expect Bonus or at least no penalty.
    assert score > 50

@patch("yfinance.Ticker")
def test_find_rolls_with_dividend(mock_ticker_cls):
    # Setup
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    
    # Mock Info with upcoming Ex-Div
    future_ex_date_ts = (datetime.utcnow() + timedelta(days=2)).timestamp()
    mock_ticker.info = {
        "exDividendDate": future_ex_date_ts,
        "dividendRate": 4.00 
    }
    mock_ticker.fast_info = {'last_price': 100.0, 'previous_close': 99.0}
    mock_ticker.options = ("2026-02-20",)
    
    # Mock Chain
    mock_chain = MagicMock()
    # Call Option Price 5.50 (Intrinsic 0? No Stk 100. If Strike 100 -> Intrinsic 0).
    # If Strike 90 -> Intrinsic 10. Price 10.50 -> Extrinsic 0.50
    # Dividend 1.00 (4/4). Extrinsic 0.50 < 1.00 -> RISK!
    
    import pandas as pd
    df = pd.DataFrame([{
        'strike': 90.0,
        'ask': 10.60, 
        'bid': 10.70, # Yields +0.10 Credit. Extrinsic 0.70 < 1.00 -> RISK!
        'lastPrice': 10.50,
        'impliedVolatility': 0.2
    }])
    mock_chain.calls = df
    mock_ticker.option_chain.return_value = mock_chain
    
    service = RollService()
    # Current Pos: Short 90 Call.
    # New Roll: 90 Call (Calendar Roll) expiring in future.
    # Ex-Div is in 2 days. 
    # Extrinsic (0.40) < Div (1.00). 
    # Score should be Low (-50 penalty).
    
    res = service.find_rolls("T", 90.0, "2026-01-01", "call")
    
    assert "rolls" in res
    rolls = res["rolls"]
    assert len(rolls) > 0
    roll = rolls[0]
    
    # Base 50. Gamma/Delta/etc might be neutral. 
    # Penalty -50.
    # Score should be near 0 or < 30.

@patch("app.services.dividend_scanner.OpportunityService")
@patch("app.services.dividend_scanner.MongoClient")
@patch("yfinance.Ticker")
def test_dividend_scanner(mock_ticker_cls, mock_mongo, mock_opp_service):
    # Setup Mock DB
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_db.ibkr_holdings.find_one.return_value = None # No holdings map for this test
    
    from app.services.dividend_scanner import DividendScanner
    scanner = DividendScanner()
    
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    
    # 1. Good Opportunity (Ex-Div in 5 days, Yield 5%)
    now = datetime.utcnow()
    ex_date = now + timedelta(days=5)
    mock_ticker.info = {
        "exDividendDate": ex_date.timestamp(),
        "dividendRate": 5.00,
        "currentPrice": 100.00, # Yield 5%
        "previousClose": 100.00
    }
    
    opps = scanner.scan_dividend_capture_opportunities(["VZ"])
    
    assert len(opps) == 1
    assert opps[0]["symbol"] == "VZ"
    assert opps[0]["yield_annual"] == 5.0
    
    # 2. Too Far Away (40 days)
    ex_date_far = now + timedelta(days=40)
    mock_ticker.info["exDividendDate"] = ex_date_far.timestamp()
    
    opps_far = scanner.scan_dividend_capture_opportunities(["VZ"])
    assert len(opps_far) == 0
    
    # 3. Low Yield (1%)
    ex_date_near = now + timedelta(days=5)
    mock_ticker.info["exDividendDate"] = ex_date_near.timestamp()
    mock_ticker.info["dividendRate"] = 1.00 # 1% yield
    
    opps_low = scanner.scan_dividend_capture_opportunities(["VZ"])
    assert len(opps_low) == 0



@patch("app.services.opportunity_service.OpportunityService")
@patch("app.services.dividend_scanner.DividendScanner")
def test_api_scan_dividend_capture_handling(mock_scanner_cls, mock_opp_service):
    from app.api.routes import scan_dividend_capture, router
    from app.database import get_db
    from fastapi import HTTPException
    
    # Mock DB Dependency
    mock_db = MagicMock()
    
    # 1. Test Empty Portfolio (Success, returns empty list)
    mock_db.ibkr_holdings.find_one.return_value = None # No latest snapshot
    
    # Helper to clean up scan arguments since we are testing function directly or via DI?
    # If we test function directly, we pass mock_db as argument.
    # Note: `scan_dividend_capture` now requires `db` argument.
    
    mock_user = MagicMock()
    mock_user.username = "test_user"

    res = scan_dividend_capture(mock_user, db=mock_db, force_scan=True)
    assert res == []
    
    # 2. Test Exception Handling (Should raise HTTPException 500)
    mock_db.ibkr_holdings.find_one.side_effect = Exception("Database Down")
    
    try:
        scan_dividend_capture(mock_user, db=mock_db, force_scan=True)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert "Database Down" in str(e.detail)
        
    # 3. Test Scanner Exception
    mock_db.ibkr_holdings.find_one.side_effect = None
    mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "123"}
    mock_db.ibkr_holdings.find.return_value = [{"symbol": "AAPL"}]
    
    # Configure the mock instance returned by the class constructor
    mock_scanner_instance = mock_scanner_cls.return_value
    mock_scanner_instance.scan_dividend_capture_opportunities.side_effect = Exception("Scanner API Error")
    
    try:
        scan_dividend_capture(mock_user, db=mock_db, force_scan=True)
        assert False, "Should have raised HTTPException on scanner failure"
    except HTTPException as e:
        assert e.status_code == 500
        assert "Scanner API Error" in str(e.detail)
