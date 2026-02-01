from pymongo import MongoClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def discover_and_track_tickers():
    """
    Scans the latest IBKR portfolio holdings to find symbols and underlying symbols (for options).
    Adds any new discoveries to the 'tracked_tickers' list in MongoDB.
    Returns the list of newly added tickers.
    """
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")

        # 1. Get Current Tracked List
        doc = db.system_config.find_one({"_id": "tracked_tickers"})
        tracked_list = doc["tickers"] if doc and "tickers" in doc else []
        tracked_set = set(tracked_list)

        # 2. Find latest snapshot to get current holdings
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        if not latest:
            return []

        snapshot_id = latest.get("snapshot_id")
        query = {"snapshot_id": snapshot_id} if snapshot_id else {"report_date": latest.get("report_date")}
        
        # 3. Get distinct symbols
        # Stocks: Use 'symbol'
        stk_query = query.copy()
        stk_query["asset_class"] = "STK"
        stk_syms = set(db.ibkr_holdings.distinct("symbol", stk_query))
        
        # Options: Use 'underlying_symbol'
        opt_query = query.copy()
        opt_query["asset_class"] = "OPT"
        opt_syms = set(db.ibkr_holdings.distinct("underlying_symbol", opt_query))
        
        # Combine all sources
        all_raw_syms = stk_syms.union(opt_syms)
        
        # Normalize and Filter
        portfolio_set = {s.upper().strip() for s in all_raw_syms if s}
        
        # 4. Find new tickers
        new_tickers = portfolio_set - tracked_set
        
        if new_tickers:
            new_list = list(new_tickers)
            logger.info(f"Discovered {len(new_list)} new tickers from portfolio: {new_list}")
            
            # Update DB
            db.system_config.update_one(
                {"_id": "tracked_tickers"},
                {"$addToSet": {"tickers": {"$each": new_list}}},
                upsert=True
            )
            return new_list
            
        return []

    except Exception as e:
        logger.error(f"Error in discover_and_track_tickers: {e}")
        return []
