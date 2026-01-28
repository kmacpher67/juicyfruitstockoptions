
import json
import os
from bson import json_util
# Ai_Stock_Database is mapped to /app/Ai_Stock_Database.py, so we can import it
from Ai_Stock_Database import AiStockDatabase

def restore_data(input_file="mongo_backup.json"):
    print(f"Reading backup from {input_file}...")
    try:
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} not found.")
            return

        with open(input_file, 'r') as f:
            data = json_util.loads(f.read())
        
        print(f"Found {len(data)} records in backup.")
        
        db = AiStockDatabase()
        print(f"Connected to {db.db_name}.{db.collection_name}")
        
        print("Starting restore...")
        db.upsert_many(data, key_fields=("Ticker", "Last Update"))
        
        count = db.collection.count_documents({})
        print(f"Restore Complete. Collection now has {count} documents.")

    except Exception as e:
        print(f"Error during restore: {e}")
        # raise # Don't raise, just print

if __name__ == "__main__":
    restore_data()
