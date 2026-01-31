from pymongo import MongoClient
import os
from app.config import settings

def update_ibkr_config():
    try:
        print(f"Connecting to Mongo at: {settings.MONGO_URI.split('@')[-1] if '@' in settings.MONGO_URI else 'localhost'}")
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # User Provided IDs
        updates = {
            "query_id_nav_1d": "1388009",
            "query_id_nav_7d": "1388401",
            "query_id_nav_30d": "1388404",
            "query_id_nav_mtd": "1388576",
            "query_id_nav_ytd": "1388580",
            "query_id_nav_1y": "1388410"
        }
        
        print("Updating IBKR Config with:")
        for k, v in updates.items():
            print(f"  {k}: {v}")
            
        result = db.system_config.update_one(
            {"_id": "ibkr_config"},
            {"$set": updates},
            upsert=True
        )
        
        print(f"Update Result: Matched={result.matched_count}, Modified={result.modified_count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_ibkr_config()
