from pymongo import MongoClient
import os

class AiStockDatabase:
    def __init__(self, mongo_uri=None, db_name="stocklive", collection_name="stock_data"):
        self.mongo_uri = mongo_uri or os.environ.get("MONGO_URI", "mongodb://localhost:27017/stocklive")
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.setup()

    def setup(self):
        """Setup the MongoDB connection and collection."""
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        # Create collection if it doesn't exist
        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)
        self.collection = self.db[self.collection_name]

    def upsert_stock_record(self, record, key_fields=("Ticker",)):
        """Upsert a stock record based on key_fields."""
        query = {k: record[k] for k in key_fields if k in record}
        if not query:
            raise ValueError("No key fields found in record for upsert.")
        self.collection.update_one(query, {"$set": record}, upsert=True)

    def upsert_many(self, records, key_fields=("Ticker",)):
        """Upsert many stock records."""
        for record in records:
            try:
                self.upsert_stock_record(record, key_fields=key_fields)
            except Exception as e:
                print(f"Error upserting record {record}: {e}")

# Example usage for testing
if __name__ == "__main__":
    db = AiStockDatabase()
    db.upsert_stock_record({"Ticker": "AAPL", "price": 123.45})