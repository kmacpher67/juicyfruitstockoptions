import os
import sys
from pymongo import MongoClient

# Direct URI for host access
MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

def cleanup():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_database("stock_analysis")
        
        # Test connection
        db.list_collection_names()
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    print("Starting trades data cleanup...")
    
    # 1. Fix missing AccountId using ClientAccountID if present
    print("Looking for trades with ClientAccountID but missing AccountId...")
    # MongoDB 4.2+ support pipeline updates in update_many
    try:
        result = db.ibkr_trades.update_many(
            {"AccountId": {"$exists": False}, "ClientAccountID": {"$exists": True}},
            [{"$set": {"AccountId": "$ClientAccountID"}}]
        )
        print(f"Updated {result.modified_count} records with AccountId from ClientAccountID.")
    except Exception as e:
        print(f"Error during update: {e}")
        # Fallback for older MongoDB or if pipeline update fails
        print("Attempting fallback update...")
        count = 0
        for doc in db.ibkr_trades.find({"AccountId": {"$exists": False}, "ClientAccountID": {"$exists": True}}):
            db.ibkr_trades.update_one({"_id": doc["_id"]}, {"$set": {"AccountId": doc["ClientAccountID"]}})
            count += 1
        print(f"Updated {count} records using fallback method.")
    
    # 2. Identify records missing both
    missing_both = db.ibkr_trades.count_documents({"AccountId": {"$exists": False}, "ClientAccountID": {"$exists": False}})
    if missing_both > 0:
        print(f"WARNING: {missing_both} records are still missing account information.")
    
    # 3. Validation: TradeID and Symbol are mandatory
    missing_id = db.ibkr_trades.count_documents({"trade_id": {"$exists": False}, "TradeID": {"$exists": False}})
    if missing_id > 0:
        print(f"Removing {missing_id} records missing trade_id...")
        db.ibkr_trades.delete_many({"trade_id": {"$exists": False}, "TradeID": {"$exists": False}})
        
    missing_symbol = db.ibkr_trades.count_documents({"symbol": {"$exists": False}, "Symbol": {"$exists": False}})
    if missing_symbol > 0:
        print(f"Removing {missing_symbol} records missing symbol...")
        db.ibkr_trades.delete_many({"symbol": {"$exists": False}, "Symbol": {"$exists": False}})

    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
