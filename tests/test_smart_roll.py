import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.roll_service import RollService

# Helper to mock Roll Data
def create_roll(net_credit=0.0, new_strike=105.0, current_strike=100.0, days=7, delta=0.30, gamma=0.05):
    return {
        "net_credit": net_credit,
        "strike": new_strike,
        "days_extended": days,
        "delta": delta,
        "gamma": gamma,
        "expiration": "2026-02-20", # placeholder
        "bid": 1.0, 
        "cost_to_close": 0.5,
        "roll_type": "Up & Out"
    }

def create_current(strike=100.0, avg_cost=5.0):
    return {
        "strike": strike,
        "average_cost": avg_cost
    }

def create_market(one_day_chg=0.0, price=102.0):
    return {
        "one_day_change": one_day_chg,
        "current_price": price
    }


def test_score_roll_basic():
    service = RollService()
    
    # 1. Good Credit Roll (Up and Out, 7 days)
    # Credit > 0 (+20), yield bonus (+10), Strike improved (+20), Duration 7 (+10) -> ~60+50 base = 110 (capped 100)
    # Let's reduce net_credit to avoid yield bonus to see differentiation, or accept cap behavior
    roll = create_roll(net_credit=0.20, new_strike=105, current_strike=100, days=7)
    score, _ = service.score_roll(roll, create_current(), create_market())
    assert score >= 90 # Should be very high
    
    # 2. Debit Roll 
    # Debit (-20)
    roll_bad = create_roll(net_credit=-0.50, new_strike=105, current_strike=100, days=7)
    score_bad, _ = service.score_roll(roll_bad, create_current(), create_market())
    assert score_bad < score
    
    # 3. Long Duration Penalty
    # To test duration penalty vs good roll, we need to ensure we don't hit the cap on both.
    # Let's use a "mediocre" roll base.
    roll_base_short = create_roll(net_credit=0.01, new_strike=100, current_strike=100, days=7) 
    # Score: 50 + 20 (Credit) + 10 (Duration) + 10 (Delta) = 90
    
    roll_base_long = create_roll(net_credit=0.01, new_strike=100, current_strike=100, days=45)
    # Score: 50 + 20 (Credit) - 10 (Duration) + 10 (Delta) = 70
    
    s_short, _ = service.score_roll(roll_base_short, create_current(), create_market())
    s_long, _ = service.score_roll(roll_base_long, create_current(), create_market())
    
    assert s_long < s_short


@patch("app.services.roll_service.RollService.find_rolls")
@patch("app.services.ibkr_service.fetch_flex_report") # Mock or just pass list
def test_analyze_portfolio_rolls(mock_report, mock_find_rolls):
    service = RollService()
    
    # Needs to be close to NOW for the "expiry window" filter (default 10 days)
    # Current mocked NOW in service is not mocked, it uses datetime.utcnow().
    # Test file doesn't freeze time.
    # Let's calculate a date 5 days from now.
    near_expiry = (datetime.utcnow() + timedelta(days=5)).strftime("%Y%m%d")
    
    # Mock Holdings
    portfolio = [
        {"symbol": "AAPL", "secType": "OPT", "right": "C", "quantity": -1, "strike": 150, "expiry": near_expiry}, # Short Call, Near Term
        {"symbol": "MSFT", "secType": "STK", "quantity": 100}, # Stock (ignore)
        {"symbol": "GOOG", "secType": "OPT", "right": "P", "quantity": -1}, # Short Put (ignore for now?) specific logic for calls
    ]
    
    # Mock find_rolls return
    mock_find_rolls.return_value = {
        "symbol": "AAPL", 
        "rolls": [
            {"strike": 155, "net_credit": 0.50, "score": 85} # Mock score already there? Service should add it.
        ] 
    }
    # Act
    # We need to inject the portfolio list. The method signature says `analyze_portfolio_rolls(portfolio_items)`
    results = service.analyze_portfolio_rolls(portfolio)
    
    # Assert
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
    mock_find_rolls.assert_called_once()

    
@patch("app.api.routes.MongoClient")
@patch("app.services.roll_service.RollService.analyze_portfolio_rolls")
def test_get_smart_rolls_endpoint(mock_analyze, mock_mongo):
    from app.api.routes import analyze_smart_rolls
    from app.models import User
    
    # Mock User
    user = User(username="test", email="test@test.com", role="portfolio")
    
    # Mock DB
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "123"}
    mock_db.ibkr_holdings.find.return_value = [{"symbol": "AAPL"}] # Dummy holding
    
    # Mock Service Return
    mock_analyze.return_value = [{"symbol": "AAPL", "rolls": []}]
    
    # Act
    response = analyze_smart_rolls(user)
    
    # Assert
    assert len(response) == 1
    assert response[0]["symbol"] == "AAPL"
    mock_analyze.assert_called_once()
