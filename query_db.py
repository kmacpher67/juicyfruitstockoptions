from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017/")
db = client.get_database("stock_analysis")
doc = db.ibkr_trades.find_one()
if doc:
    doc.pop('_id', None)
    print(json.dumps(doc, indent=2))
else:
    print("No trades found")
