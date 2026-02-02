from pymongo import MongoClient
from app.config import settings

def get_stock_collection():
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    return db.stock_data

def run_scanner(criteria: dict):
    """
    Run a query against the stock_data collection.
    Criteria is a list of filters (e.g., {"field": "TSMOM_60", "op": "gt", "value": 0}).
    """
    collection = get_stock_collection()
    query = {}
    
    # Simple query builder
    for key, condition in criteria.items():
        # Direct MongoDB query support if passed directly, 
        # or we could abstract it. Let's assume the caller passes
        # a friendly dict that we map to Mongo syntax.
        pass # To be implemented if complex parsing needed
        
    # For now, let's assume 'criteria' IS the mongo query for flexibility in the first iteration
    # But usually we want safe presets.
    
    # If criteria is empty, return all? Limit to 50.
    limit = 50
    results = list(collection.find(criteria, {"_id": 0}).limit(limit))
    return results

def scan_momentum_calls():
    """
    Preset: Find stocks with strong momentum (TSMOM or 1D change) and Up Trend.
    """
    filter_query = {
        "TSMOM_60": {"$gt": 0.05}, # > 5% Momentum
        "Current Price": {"$gt": 10}, # Filter penny stocks
        "EMA_20_highlight": {"$gt": 0.005} # Price > EMA_20 by 0.5% (Trend Up)
    }
    return run_scanner(filter_query)

def scan_juicy_candidates():
    """
    Preset: Juicy Fruit Candidates (High Volatility, Liquid).
    Note: We need IV data. Assuming we have some proxy or just using Yields.
    """
    filter_query = {
        "Annual Yield Put Prem": {"$gt": 15.0}, # > 15% Yield
        "Market Cap (T$)": {"$gt": 0.010}, # > 10B (Rough filter)
    }
    return run_scanner(filter_query)
