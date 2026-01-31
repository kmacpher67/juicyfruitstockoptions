import sys
import os
import io
from pymongo import MongoClient

# Set env var before importing app config
os.environ["MONGO_URI"] = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
sys.path.append(os.getcwd())

from app.config import settings

try:
    print("Connecting...")
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client.get_default_database("stock_analysis")
    print("Connected to:", db.name)
    
    latest_holding = db.ibkr_holdings.find_one(sort=[("date", -1)])
    print("Latest Holding:", latest_holding)
    
    if latest_holding:
        query = {"report_date": latest_holding.get("report_date")}
        if latest_holding.get("snapshot_id"):
            query = {"snapshot_id": latest_holding.get("snapshot_id")}
        
        print("Query:", query)
        count = db.ibkr_holdings.count_documents(query)
        print("Count:", count)
        
        cursor = db.ibkr_holdings.find(query)
        for doc in cursor:
            print("Doc Sample:", doc)
            print("Underlying:", doc.get("underlying_symbol"))
            print("Position:", doc.get("position"))
            break
            
    from app.services.export_service import generate_portfolio_csv_content
    print("Testing export function...")
    content = generate_portfolio_csv_content()
    print("Content Length:", len(content))
    print(content)

except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
