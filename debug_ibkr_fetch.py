import sys
import logging
from app.config import settings
from app.services.ibkr_service import fetch_flex_report

# Setup logging to console
logging.basicConfig(level=logging.INFO, format='%(message)s')

def debug_fetch():
    # 30-Day Query ID from user
    QUERY_ID = "1388404"
    
    # Needs a token. Try to get from settings or DB.
    # Since we can't easily read DB without pymongo boilerplate, let's assume valid token is in DB
    # or rely on the user having set it in .env (which is missing).
    # We will try to read the token from MongoDB directly first.
    
    from pymongo import MongoClient
    # Hardcoded Credentials from docker-compose.yml
    uri = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client.get_default_database("stock_analysis")
        if "stock_analysis" not in client.list_database_names():
             db = client["stock_analysis"] # Force use
             
        config = db.system_config.find_one({"_id": "ibkr_config"})
        token = config.get("flex_token")
        
        if not token:
            print("ERROR: No Flex Token found in DB.")
            return

        print(f"Fetching Report for Query {QUERY_ID}...", flush=True)
        xml_data = fetch_flex_report(QUERY_ID, token, label="DEBUG_30D")
        
        print("\n--- RAW XML START ---")
        print(xml_data.decode('utf-8')[:5000]) # Print first 5000 chars
        print("\n--- RAW XML END ---")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_fetch()
