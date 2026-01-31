import os
from pymongo import MongoClient
from app.config import settings

def check_nav_data():
    print(f"Connecting to Mongo at: {settings.MONGO_URI.split('@')[-1] if '@' in settings.MONGO_URI else 'localhost'}")
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")

    print("\n--- IBKR Config (from DB) ---")
    config = db.system_config.find_one({"_id": "ibkr_config"})
    if config:
        for k, v in config.items():
            if "token" in k:
                print(f"{k}: *****")
            else:
                print(f"{k}: {v}")
    else:
        print("No ibkr_config found.")

    print("\n--- NAV History (Dates) ---")
    history = list(db.ibkr_nav_history.find({}, {"report_date": 1, "total_nav": 1, "source": 1}).sort("report_date", 1))
    
    if not history:
        print("No NAV history found.")
    else:
        print(f"Found {len(history)} records.")
        # Print first 5 and last 5
        for h in history[:5]:
            print(f"{h.get('report_date')}: {h.get('total_nav')} ({h.get('source', 'unknown')})")
        if len(history) > 5:
            print("...")
            for h in history[-5:]:
                print(f"{h.get('report_date')}: {h.get('total_nav')} ({h.get('source', 'unknown')})")

if __name__ == "__main__":
    check_nav_data()
