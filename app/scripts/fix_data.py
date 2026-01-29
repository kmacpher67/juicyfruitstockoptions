import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pymongo import MongoClient
from app.config import settings

def clean_data():
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Inspect Data
    pipeline = [
        {
            "$group": {
                "_id": "$snapshot_id",
                "count": {"$sum": 1},
                "total_nav": {"$sum": "$market_value"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = list(db.ibkr_holdings.aggregate(pipeline))
    print("--- Current Snapshots ---")
    bad_ids = []
    
    for r in results:
        sid = r["_id"]
        count = r["count"]
        nav = r["total_nav"]
        print(f"ID: {sid} | Count: {count} | NAV: ${nav:,.2f}")
        
        # Heuristic: If NAV > 3M, it's likely double-counted (User said ~1.7M is expected, currently seeing 4M)
        if nav > 3_000_000:
            bad_ids.append(sid)
            
    # 2. Delete Bad Snapshots
    if bad_ids:
        print(f"\nDeleting {len(bad_ids)} suspect snapshots...")
        result = db.ibkr_holdings.delete_many({"snapshot_id": {"$in": bad_ids}})
        print(f"Deleted {result.deleted_count} documents.")
    else:
        print("\nNo obvious bad snapshots found (NAV > 3M).")

if __name__ == "__main__":
    clean_data()
