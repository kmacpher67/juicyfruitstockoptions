import json
from datetime import datetime
from pymongo import MongoClient
import os

# Connect to Mongo (try unauthenticated first as per recent test)
# User provided URI in docker-compose, but local test worked without auth.
client = MongoClient("mongodb://localhost:27017")
db = client["stock_analysis"]
collection = db["stock_data"]

def restore():
    input_file = "mongo_backup.json"
    if not os.path.exists(input_file):
        print("Backup file not found.")
        return

    with open(input_file, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records from {input_file}")
    
    upserted = 0
    errors = 0

    for record in data:
        try:
            # Clean _id (let mongo generate new one or keep existing if using $oid)
            if "_id" in record:
                del record["_id"]
            
            # Upsert Key: Ticker + Last Update
            # Ensure "Last Update" exists
            if "Last Update" in record and "Ticker" in record:
                # Upsert to avoid duplicates
                collection.update_one(
                    {"Ticker": record["Ticker"], "Last Update": record["Last Update"]},
                    {"$set": record},
                    upsert=True
                )
                upserted += 1
            else:
                print(f"Skipping record without Ticker/LastUpdate: {record.keys()}")
                errors += 1
        except Exception as e:
            print(f"Error inserting record: {e}")
            errors += 1

    print(f"Restore Complete: {upserted} upserted, {errors} skipped/failed.")

if __name__ == "__main__":
    restore()
