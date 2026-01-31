from app.services.ibkr_service import parse_csv_nav
from app.config import settings
from pymongo import MongoClient
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Monkeypatch Settings for Local Execution
settings.MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

def verify_fix():
    # 1. Sample CSV Data (from previous debug_ibkr_fetch output)
    sample_csv = """
"ClientAccountID","AccountAlias","Model","CurrencyPrimary","FromDate","ToDate","StartingValue","Mtm","EndingValue"
"U110638","","","USD","20251230","20260128","352096.99","16161.93","368208.38"
    """.strip()
    
    print("Testing parse_csv_nav with sample data...")
    parse_csv_nav(sample_csv)
    
    # 2. Check DB for Historical Record
    # Use hardcoded admin URI for verification
    uri = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
    client = MongoClient(uri)
    db = client.get_default_database("stock_analysis")
    if "stock_analysis" not in client.list_database_names():
         db = client["stock_analysis"]
         
    # We expect a record for 2025-12-30 (FromDate) with value 352096.99
    target_date = "2025-12-30"
    print(f"\nChecking DB for record on {target_date}...")
    
    record = db.ibkr_nav_history.find_one({"report_date": target_date, "account_id": "U110638"})
    
    if record:
        print("SUCCESS! Found Historical Record:")
        print(f"  Date: {record.get('report_date')}")
        print(f"  NAV: {record.get('total_nav')}")
        print(f"  Source: {record.get('source')}")
    else:
        print("FAILURE: Record not found.")

if __name__ == "__main__":
    verify_fix()
