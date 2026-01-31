
import sys
import os
from pymongo import MongoClient

# Hardcoded URI to avoid import issues if config is bad
MONGO_URI = "mongodb://mongo:27017"

print("DEBUG V3 START", file=sys.stderr)

try:
    client = MongoClient(MONGO_URI)
    db = client.stock_analysis
    
    print("Connected to DB", file=sys.stderr)
    
    print("\n--- 7D Detail ---")
    latest = db.ibkr_nav_history.find_one({"ibkr_report_type": "Nav7D"}, sort=[("_report_date", -1)])
    if latest:
        d = latest["_report_date"]
        print(f"Latest 7D Date: {d}")
        cursor = db.ibkr_nav_history.find({"ibkr_report_type": "Nav7D", "_report_date": d})
        total_start = 0
        total_end = 0
        print(f"{'Account':<15} {'Start':<15} {'End':<15} {'Change%':<10}")
        for doc in cursor:
            s = doc.get("starting_value", 0)
            e = doc.get("ending_value", 0)
            chg = ((e - s)/s)*100 if s else 0
            print(f"{doc.get('account_id'):<15} {s:<15} {e:<15} {chg:.2f}%")
            total_start += s
            total_end += e
            
        print("-" * 60)
        final_chg = ((total_end - total_start)/total_start)*100 if total_start else 0
        print(f"{'TOTAL':<15} {total_start:<15} {total_end:<15} {final_chg:.2f}%")
    else:
        print("No 7D records found.", file=sys.stderr)

except Exception as e:
    import traceback
    traceback.print_exc()
