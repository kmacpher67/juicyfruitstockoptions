import json
import os
import argparse
from pymongo import MongoClient
from bson import json_util

DEFAULT_MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
DEFAULT_DB_NAME = "stock_analysis"
DEFAULT_COLLECTION_NAME = "stock_data"


def restore_data(
    input_file="mongo_backup.json",
    mongo_uri=None,
    db_name=None,
    collection_name=None,
):
    mongo_uri = mongo_uri or os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)
    db_name = db_name or os.environ.get("MONGO_DB_NAME", DEFAULT_DB_NAME)
    collection_name = collection_name or os.environ.get(
        "MONGO_COLLECTION_NAME", DEFAULT_COLLECTION_NAME
    )

    print(f"Reading backup from {input_file}...")
    try:
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} not found.")
            raise FileNotFoundError(input_file)

        with open(input_file, "r", encoding="utf-8") as f:
            data = json_util.loads(f.read())

        print(f"Found {len(data)} records in backup.")

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        collection = client[db_name][collection_name]

        print(f"Connected to {db_name}.{collection_name}")
        print("Starting restore...")

        restored = 0
        for record in data:
            query = {
                key: record[key]
                for key in ("Ticker", "Last Update")
                if key in record
            }
            if not query:
                raise ValueError(
                    "Backup record is missing both 'Ticker' and 'Last Update' keys."
                )
            collection.update_one(query, {"$set": record}, upsert=True)
            restored += 1

        count = collection.count_documents({})
        print(f"Upserted {restored} records.")
        print(f"Restore Complete. Collection now has {count} documents.")

    except Exception as e:
        print(f"Error during restore: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Restore a JSON Mongo backup into a running MongoDB instance."
    )
    parser.add_argument(
        "--input-file",
        default="mongo_backup.json",
        help="Path to the exported backup JSON file.",
    )
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="MongoDB connection string. Defaults to the local Docker Mongo instance.",
    )
    parser.add_argument(
        "--db-name",
        default=None,
        help="MongoDB database name. Defaults to stock_analysis.",
    )
    parser.add_argument(
        "--collection-name",
        default=None,
        help="MongoDB collection name. Defaults to stock_data.",
    )
    args = parser.parse_args()
    restore_data(
        input_file=args.input_file,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        collection_name=args.collection_name,
    )


if __name__ == "__main__":
    main()
