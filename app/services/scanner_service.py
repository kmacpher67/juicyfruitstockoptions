from pymongo import MongoClient
from app.config import settings

from app.services.opportunity_service import OpportunityService
from app.models.opportunity import JuicyOpportunity, OpportunityStatus
import logging

def get_stock_collection():
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    return db.stock_data

def run_scanner(criteria: dict, persist: bool = False, trigger_source: str = "Scanner"):
    """
    Run a query against the stock_data collection.
    Criteria is a list of filters (e.g., {"field": "TSMOM_60", "op": "gt", "value": 0}).
    """
    collection = get_stock_collection()
    
    # Simple query builder - assume criteria fits Mongo structure for now
    
    # Limit to 50
    limit = 50
    results = list(collection.find(criteria, {"_id": 0}).limit(limit))
    
    if persist and results:
        _persist_results(results, trigger_source)
        
    return results

def _persist_results(results, trigger_source):
    """Persist results to Opportunities collection."""
    opp_service = OpportunityService()
    for item in results:
        try:
             symbol = item.get("Ticker")
             if not symbol: continue
             
             # Avoid spamming if data hasn't changed? 
             # For now, we trust the scheduler frequency.
             
             opp = JuicyOpportunity(
                 symbol=symbol,
                 trigger_source=trigger_source,
                 status=OpportunityStatus.DETECTED,
                 context={
                     "current_price": item.get("Current Price"),
                     "tsmom_60": item.get("TSMOM_60"),
                     "put_yield": item.get("Annual Yield Put Prem")
                 },
                 proposal=item 
             )
             opp_service.create_opportunity(opp)
             logging.info(f"Persisted {trigger_source} opportunity for {symbol}")
        except Exception as e:
             logging.error(f"Failed to persist {symbol}: {e}")

def scan_momentum_calls(persist: bool = False):
    """
    Preset: Find stocks with strong momentum (TSMOM or 1D change) and Up Trend.
    """
    filter_query = {
        "TSMOM_60": {"$gt": 0.05}, # > 5% Momentum
        "Current Price": {"$gt": 10}, # Filter penny stocks
        "EMA_20_highlight": {"$gt": 0.005} # Price > EMA_20 by 0.5% (Trend Up)
    }
    return run_scanner(filter_query, persist=persist, trigger_source="MomentumScanner")

def scan_juicy_candidates(persist: bool = False):
    """
    Preset: Juicy Fruit Candidates (High Volatility, Liquid).
    Note: We need IV data. Assuming we have some proxy or just using Yields.
    """
    filter_query = {
        "Annual Yield Put Prem": {"$gt": 15.0}, # > 15% Yield
        "Market Cap (T$)": {"$gt": 0.010}, # > 10B (Rough filter)
    }
    return run_scanner(filter_query, persist=persist, trigger_source="JuicyScanner")
