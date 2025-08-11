from pymongo import MongoClient
import os

mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/stocklive")
client = MongoClient(mongo_uri)
db = client.get_database()
collection = db.stock_data

# Example: insert a record
collection.insert_one({"ticker": "AAPL", "price": 123.45})