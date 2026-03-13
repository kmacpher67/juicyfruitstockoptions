from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.get_database("stock_analysis")
print(db.list_collection_names())
