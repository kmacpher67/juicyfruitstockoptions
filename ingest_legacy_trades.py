import os
import csv
import logging
import glob
from pymongo import MongoClient
from app.config import settings
from app.models import TradeRecord

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def normalize_key(key):
    """Normalize CSV header key to remove spaces and match common aliases."""
    if not key: return ""
    clean = key.strip()
    # Removing spaces for mapping to clean dictionary keys if needed, 
    # but for TradeRecord we use aliases or exact matches. 
    # Let's keep spaces in the 'raw' dict to match the headers, 
    # but we might want to map specific critical fields.
    return clean

def normalize_row(row):
    """
    Convert a CSV row (dict) into a clean dictionary for MongoDB.
    Handles key mapping for TradeID/TransactionID.
    """
    # 1. Strip whitespace from keys and values
    clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
    
    # 2. Identify TradeID
    # Common variations: "TradeID", "TransactionID", "IBTransactionID"
    trade_id = clean_row.get("TradeID") or clean_row.get("TransactionID") or clean_row.get("IBTransactionID")
    
    if not trade_id:
        return None # Skip rows without ID (subtotals, etc.)
        
    # Ensure TradeID is set for the model
    clean_row["TradeID"] = trade_id
    
    # 3. Handle Quantity/Price/Comm parsing safely
    try:
        if "Quantity" in clean_row: clean_row["Quantity"] = float(clean_row["Quantity"].replace(',', ''))
        if "TradePrice" in clean_row: clean_row["TradePrice"] = float(clean_row["TradePrice"].replace(',', ''))
        if "IBCommission" in clean_row: clean_row["IBCommission"] = float(clean_row["IBCommission"].replace(',', ''))
        if "NetCash" in clean_row: clean_row["NetCash"] = float(clean_row["NetCash"].replace(',', ''))
    except ValueError:
        pass # Keep as string if parsing fails, but Model might complain if defined as float.
        # TradeRecord optional float fields should handle it or fail validation.
        
    return clean_row

def ingest_file(filepath, db):
    """Ingest a single CSV file."""
    filename = os.path.basename(filepath)
    print(f"Processing {filename}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f: # utf-8-sig handles BOM
            # Check for header
            # Some IBKR files might have pre-headers. 
            # We assume "Symbol" is in the header line.
            lines = f.readlines()
            start_idx = 0
            for i, line in enumerate(lines):
                if "Symbol" in line and ("Buy/Sell" in line or "TradeID" in line or "Quantity" in line):
                    start_idx = i
                    break
            
            if start_idx >= len(lines):
                 logging.warning(f"Skipping {filename}: Could not find header.")
                 return

            # Re-read with DictReader from start_idx
            f.seek(0)
            # Skip lines before header
            for _ in range(start_idx): next(f)
            
            reader = csv.DictReader(f)
            count = 0
            updated = 0
            
            for row in reader:
                doc = normalize_row(row)
                if not doc: continue
                
                # Validation with Pydantic (Optional, ensures minimal quality)
                # We can store the raw doc, but let's try to fit into TradeRecord for critical fields
                # and let 'extra' capture the rest.
                try:
                    # Validate
                    record = TradeRecord(**doc)
                    final_doc = record.model_dump()
                    
                    # 4. Upsert to MongoDB
                    # Idempotent: use trade_id (snake_case)
                    res = db.ibkr_trades.update_one(
                        {"trade_id": final_doc["trade_id"]}, 
                        {"$set": final_doc},
                        upsert=True
                    )
                    
                    if res.upserted_id or res.modified_count > 0:
                        updated += 1
                    count += 1
                    
                except Exception as e:
                    logging.warning(f"Validation failed for row in {filename}: {e}")
                    continue
                    
            print(f"Finished {filename}: Processed {count} trades (Upserted/Updated: {updated})")
            
    except Exception as e:
        logging.error(f"Failed to process {filename}: {e}")

def main():
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Pattern to match all Recent_Trades CSVs
    files = glob.glob("ibkr-legacy-data/Recent_Trades*.csv")
    files.sort() # Process in order, though Idempotency makes order less critical
    
    print(f"Found {len(files)} files to ingest.")
    
    for filepath in files:
        ingest_file(filepath, db)

if __name__ == "__main__":
    main()
