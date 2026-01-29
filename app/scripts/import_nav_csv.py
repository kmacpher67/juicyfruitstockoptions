import sys
import os
import csv
import logging
from datetime import datetime

# Setup paths (if run as script)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.config import settings
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_ibkr_date(date_str):
    """Converts 20251231 to 2025-12-31."""
    if not date_str: return None
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None

def import_nav_csv(filepath):
    """
    Parses IBKR Activity Flex Query CSV (NAV Section).
    Handles "stacked" CSVs (multiple header blocks).
    """
    logging.info(f"Importing NAV CSV: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    count = 0
    
    # Logic: IBKR Stacked CSVs just repeat the header.
    # We can use DictReader on the whole file if we filter out headers in the middle?
    # No, headers might be different (though usually same for same query).
    # Safer: Iterate lines, if line starts with "ClientAccountID", it's a header.
    # Grab the field mapping from that header line.
    
    headers = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check if Header
        if line.startswith('"ClientAccountID"'):
            # Parse header to get column indices map
            # Assuming standard quote parsing
            reader = csv.reader([line])
            headers = next(reader)
            continue
            
        if not headers:
            continue # Skip until first header found
            
        # Parse Data Row
        reader = csv.reader([line])
        try:
            row_values = next(reader)
        except StopIteration:
            continue
            
        if len(row_values) != len(headers):
            continue # Mismatch or EOF junk
            
        # Create Dict
        row = dict(zip(headers, row_values))
        
        # Extract desired fields
        acct_id = row.get("ClientAccountID")
        to_date_raw = row.get("ToDate")
        ending_val = row.get("EndingValue")
        currency = row.get("CurrencyPrimary")
        
        if not (acct_id and to_date_raw and ending_val):
            continue
            
        report_date = parse_ibkr_date(to_date_raw)
        if not report_date:
            continue
            
        try:
            total_nav = float(ending_val)
        except ValueError:
            logging.warning(f"Invalid EndingValue for {acct_id}: {ending_val}")
            continue
            
        # UPSERT
        # Key: Account + ReportDate
        filter_query = {
            "account_id": acct_id,
            "report_date": report_date,
            "source": "NAV_CSV"
        }
        
        update_doc = {
            "account_id": acct_id,
            "report_date": report_date,
            "total_nav": total_nav,
            "currency": currency,
            "source": "NAV_CSV",
            "ingested_at": datetime.utcnow()
        }
        
        db.ibkr_nav_history.update_one(
            filter_query,
            {"$set": update_doc},
            upsert=True
        )
        count += 1
        
    logging.info(f"Imported {count} NAV records.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", help="Path to NAV CSV file")
    args = parser.parse_args()
    
    import_nav_csv(args.filepath)
