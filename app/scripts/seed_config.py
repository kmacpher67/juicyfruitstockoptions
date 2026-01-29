import sys
import os

# Ensure we can import from app
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import MongoClient
from app.config import settings

def seed_config():
    print("Connecting to MongoDB...")
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    config_collection = db["system_config"]

    # IBKR Token
    # Ideally should be encrypted, but for MVP we store in secured DB collection
    ibkr_token = "227659255305369040956931" 
    
    print(f"Seeding IBKR Token...")
    
    result = config_collection.update_one(
        {"_id": "ibkr_config"},
        {"$set": {
            "flex_token": ibkr_token,
            "query_id_holdings": "Daily_Portfolio", # User to replace with numeric ID
            "query_id_trades": "Recent_Trades"      # User to replace with numeric ID
        }},
        upsert=True
    )
    
    action = "Updated" if result.matched_count > 0 else "Created"
    print(f"IBKR Config: {action}")
    print("Config seeding complete.")

if __name__ == "__main__":
    seed_config()
