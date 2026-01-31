import sys
import os
import pymongo
from app.config import settings

# Force URI if needed, or rely on app config default
# settings.MONGO_URI should work if environment is correct.

def debug_live_data():
    try:
        client = pymongo.MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        print("Connected to DB:", db.name)
        
        # 1. Check Latest Holdings
        latest_holding = db.ibkr_holdings.find_one(sort=[("date", -1)])
        if not latest_holding:
            print("ERROR: No holdings found at all in 'ibkr_holdings'.")
            return

        print(f"Latest Report Date: {latest_holding.get('report_date')}")
        print(f"Latest Snapshot ID: {latest_holding.get('snapshot_id')}")
        
        query = {"report_date": latest_holding.get("report_date")}
        if latest_holding.get("snapshot_id"):
            query = {"snapshot_id": latest_holding.get("snapshot_id")}
            
        print(f"Querying with: {query}")
        
        count = db.ibkr_holdings.count_documents(query)
        print(f"Found {count} documents.")
        
        # Inspect first 3 docs
        cursor = db.ibkr_holdings.find(query).limit(3)
        for i, doc in enumerate(cursor):
            print(f"\n--- Doc {i} ---")
            print(f"Symbol: {doc.get('symbol')}")
            print(f"Underlying: {doc.get('underlying_symbol')}")
            print(f"Position: {doc.get('position')} (Type: {type(doc.get('position'))})")
            print(f"Avg Cost: {doc.get('avg_cost')}")
            print(f"Cost Basis: {doc.get('cost_basis')}")
            
    except Exception as e:
        print(f"Debug crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_live_data()
