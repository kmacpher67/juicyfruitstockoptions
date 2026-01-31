from pymongo import MongoClient
import os

MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
client = MongoClient(MONGO_URI)
db = client.get_default_database("stock_analysis")

print("--- Checking Nav7D Freshness ---")
latest = db.ibkr_nav_history.find_one(
    {"ibkr_report_type": "Nav7D"},
    sort=[("_report_date", -1)]
)

if latest:
    print(f"Report: Nav7D | Latest Date: {latest.get('_report_date')} | Ending Value: {latest.get('ending_value')}")
else:
    print("Nav7D: No Data Found")
