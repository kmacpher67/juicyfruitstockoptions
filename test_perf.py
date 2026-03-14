import time
from pymongo import MongoClient
import sys
import os

# Set up to import from app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.trade_analysis import calculate_pnl

def test_performance():
    client = MongoClient("mongodb://localhost:27017/")
    db = client.get_default_database("stock_analysis")
    
    print("Fetching documents...")
    t0 = time.time()
    docs = list(db.ibkr_trades.find({}).sort("date_time", 1))
    t1 = time.time()
    print(f"Fetched {len(docs)} documents in {t1 - t0:.3f}s")
    
    # Simulate fix_oid
    def fix_oid(doc):
        doc["_id"] = str(doc["_id"])
        return doc
        
    raw_trades = [fix_oid(d) for d in docs]
    
    print("Running P&L Calculation...")
    t2 = time.time()
    analyzed_trades, open_positions = calculate_pnl(raw_trades)
    t3 = time.time()
    
    print(f"Calculated in {t3 - t2:.3f}s")
    print(f"Total analyzed trades: {len(analyzed_trades)}")
    print(f"First analyzed trade: {analyzed_trades[0].model_dump() if analyzed_trades else None}")

if __name__ == "__main__":
    test_performance()
