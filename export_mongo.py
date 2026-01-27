import json
import os
from datetime import datetime
from bson import json_util
from Ai_Stock_Database import AiStockDatabase

def export_data(output_file="mongo_backup.json"):
    """
    Exports all data from the MongoDB collection to a JSON file.
    Uses bson.json_util to handle MongoDB specific types like ObjectId and datetime.
    """
    print(f"Connecting to database...")
    try:
        # Use the existing helper to connect
        db_helper = AiStockDatabase()
        
        # Get count to verify we have something
        count = db_helper.collection.count_documents({})
        print(f"Found {count} documents in collection '{db_helper.collection_name}'.")
        
        if count == 0:
            print("Warning: Collection is empty. Nothing to export.")
            return

        print(f"Exporting data to {output_file}...")
        
        # Fetch all documents
        cursor = db_helper.collection.find({})
        
        # Convert to list and dump to JSON using json_util for proper type handling
        documents = list(cursor)
        
        with open(output_file, 'w') as f:
            f.write(json_util.dumps(documents, indent=2))
            
        print(f"Successfully exported {len(documents)} records to {output_file}")
        
    except Exception as e:
        print(f"Error during export: {e}")
        raise

if __name__ == "__main__":
    export_data()
