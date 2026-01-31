from pymongo import MongoClient
import sys

# DEBUG ONLY - Direct Connect
MONGO_URI = "mongodb://localhost:27017"

def inspect_nav():
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # 1. Check NAV History
        history = list(db.ibkr_nav_history.find().sort("report_date", 1))
        
        print(f"--- NAV History ({len(history)} records) ---")
        for h in history:
            print(f"Date: {h.get('report_date')} | Acct: {h.get('account_id')} | NAV: ${h.get('total_nav'):,.2f} | Src: {h.get('source')}")
            
        if not history:
            print("No NAV History found.")
            
        print("\n--- Aggregation Logic Test ---")
        # Mimic portfolio_analysis.py aggregation
        pipeline = [
            {
                "$group": {
                    "_id": "$report_date",
                    "total_nav": {"$sum": "$total_nav"},
                    "accounts": {"$addToSet": "$account_id"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        agg = list(db.ibkr_nav_history.aggregate(pipeline))
        for d in agg:
            print(f"Date: {d['_id']} | Total NAV: ${d['total_nav']:,.2f} | Accts: {len(d['accounts'])}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_nav()
