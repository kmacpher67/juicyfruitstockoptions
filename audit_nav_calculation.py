from datetime import datetime, timedelta
from pymongo import MongoClient
from app.config import settings
import sys

# Top-level script, no function defs to avoid indent/scope issues

# Hardcoded Credentials from docker-compose.yml
# mongodb://admin:admin123@mongo:27017/?authSource=admin -> localhost
uri = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

print(f"Connecting to Mongo at {uri.split('@')[-1]}...", flush=True)

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Force connection check
    info = client.server_info()
    print("Connected to server.", flush=True)
    
    db = client.get_default_database("stock_analysis")
    # Need to explicit set db if URI authSource is admin but data is in stock_analysis (usually default db applies if in URI path, but here it is not)
    if "stock_analysis" in client.list_database_names():
         db = client["stock_analysis"]
    else:
         print("Warning: stock_analysis DB not found in list, using 'stock_analysis' regardless.")
         db = client["stock_analysis"]
    
    # 1. Fetch Raw History
    print("Fetching history...", flush=True)
    history = list(db.ibkr_nav_history.find({}, {"report_date": 1, "total_nav": 1}).sort("report_date", 1))
    
    print(f"\n[RAW DATA FOUND: {len(history)} records]", flush=True)
    if not history:
        print("CRITICAL: No history found. This explains why widgets might be empty.")
        sys.exit(0)
        
    for h in history:
        print(f"  Date: {h.get('report_date')} | NAV: {h.get('total_nav')}")
        
    # 2. Replicate Logic
    date_map = {d["report_date"]: d["total_nav"] for d in history}
    sorted_dates = sorted(date_map.keys())
    current_date = sorted_dates[-1]
    current_nav = date_map[current_date]
    
    print(f"\n[CURRENT STATE]", flush=True)
    print(f"  Latest Data Date: {current_date}")
    print(f"  Current NAV: {current_nav}")
    
    def get_nav_at(target_date_str, label):
        found_date = None
        # Logic: Find closest date <= target_date
        # Since we want history, we look for data ON or BEFORE target.
        for d in sorted_dates:
            if d <= target_date_str:
                found_date = d
            else:
                break
        
        found_val = date_map.get(found_date) if found_date else None
        print(f"\n  Checking {label} (Target: {target_date_str})")
        print(f"    -> Closest Date Found: {found_date}")
        print(f"    -> Value Used: {found_val}")
        return found_val

    # Targets
    now_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    targets = {
        "1 Day": (now_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        "7 Day": (now_dt - timedelta(days=7)).strftime("%Y-%m-%d"),
        "30 Day": (now_dt - timedelta(days=30)).strftime("%Y-%m-%d"),
        "MTD": datetime(now_dt.year, now_dt.month, 1).strftime("%Y-%m-%d"),
        "YTD": datetime(now_dt.year, 1, 1).strftime("%Y-%m-%d"),
        "1 Year": (now_dt - timedelta(days=365)).strftime("%Y-%m-%d")
    }

    print(f"\n[CALCULATION AUDIT]", flush=True)
    for label, date_str in targets.items():
        val = get_nav_at(date_str, label)
        if val is None:
            print(f"    => RESULT: None (UI shows '--')")
        elif val == current_nav:
            print(f"    => RESULT: 0.00% (val {val} == cur {current_nav})")
        else:
            pct = ((current_nav - val) / val) * 100
            print(f"    => RESULT: {pct:.2f}%")

except Exception as e:
    print(f"Error: {e}")
