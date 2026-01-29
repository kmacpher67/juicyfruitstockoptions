import sys
import os
import csv
from pymongo import MongoClient
import logging
from datetime import datetime

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.config import settings

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def import_portfolio_csv(filepath):
    """Parses Daily_Portfolio CSV and inserts as a snapshot."""
    logging.info(f"Importing Portfolio: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        
    lines = content.splitlines()
    
    # 1. extract Date from BOF line (Line 1) if available
    # Format: "BOF","Account","Daily_Portfolio","1","20260128",...
    snapshot_date_str = None
    if lines[0].startswith('"BOF"'):
        parts = lines[0].split(',')
        if len(parts) >= 5:
            raw_date = parts[4].replace('"', '') # 20260128
            try:
                snapshot_date_str = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                pass
                
    if not snapshot_date_str:
        # Fallback to today if not found
        snapshot_date_str = datetime.utcnow().strftime("%Y-%m-%d")
        logging.warning(f"Could not parse date from BOF, using {snapshot_date_str}")
        
    # Create a unique snapshot timestamp (mid-day if unknown time, or just 00:00:00)
    # The user wants "datetime stamped". Let's use the file date at 00:00:00 UTC
    snapshot_dt = datetime.strptime(snapshot_date_str, "%Y-%m-%d")
    
    # 2. Parse Rows
    # Find Header
    start_idx = 0
    for i, line in enumerate(lines):
        if "Symbol" in line and "Quantity" in line:
            start_idx = i
            break
            
    reader = csv.DictReader(lines[start_idx:])
    positions = []
    
    for row in reader:
        if not row.get("Symbol"): continue
        
        try:
            # Map fields safely
            doc = {
                "date": snapshot_dt, # Ingestion time (backdated)
                "report_date": snapshot_date_str, 
                "snapshot_id": snapshot_dt, # UNIQUE KEY
                "account_id": row.get("ClientAccountID") or row.get("AccountId"),
                "symbol": row.get("Symbol"),
                "underlying_symbol": row.get("UnderlyingSymbol") or row.get("Symbol"),
                "asset_class": row.get("AssetClass"),
                "quantity": float(row.get("Quantity") or 0),
                "cost_basis": float(row.get("CostBasisPrice") or 0),
                "market_price": float(row.get("MarkPrice") or 0),
                "market_value": float(row.get("PositionValue") or row.get("MarkValue") or 0),
                "percent_of_nav": float(row.get("PercentOfNAV") or 0) / 100.0,
                "unrealized_pnl": float(row.get("FifoPnlUnrealized") or 0)
            }
            positions.append(doc)
        except ValueError:
            continue

    if positions:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # Check if snapshot exists?
        # User requested per-day unique key. 
        # If we re-run this script, we might duplicate if we don't clean up SAME snapshot_id.
        existing = db.ibkr_holdings.count_documents({"snapshot_id": snapshot_dt})
        if existing > 0:
            logging.info(f"Snapshot {snapshot_dt} already exists ({existing} docs). Overwriting...")
            db.ibkr_holdings.delete_many({"snapshot_id": snapshot_dt})
            
        db.ibkr_holdings.insert_many(positions)
        logging.info(f"Successfully imported {len(positions)} holdings for Snapshot: {snapshot_date_str}")
    else:
        logging.error("No positions found.")

def import_trades_csv(filepath):
    """Parses Recent_Trades CSV and upserts."""
    logging.info(f"Importing Trades: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        
    start_idx = 0
    for i, line in enumerate(lines):
        if "Symbol" in line and "Buy/Sell" in line:
            start_idx = i
            break
            
    reader = csv.DictReader(lines[start_idx:])
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    count = 0 
    for row in reader:
        # Map fields
        trade_id = row.get("TradeID") or row.get("TransactionID") or row.get("IBTransactionID")
        if not trade_id: continue
        
        try:
             # Manual CSV has "UnderlyingSecurityID" but maybe not Symbol?
             # User file: "Symbol","Description","UnderlyingSecurityID"
             # It seems to lack "UnderlyingSymbol" column explicitly?
             # Wait, row 2: "AMZN","AMAZON...","","" ...
             # We might need to infer Underlying from Symbol for stocks.
             sym = row.get("Symbol")
             underlying = row.get("UnderlyingSymbol") 
             if not underlying and row.get("AssetClass") == "STK":
                 underlying = sym
             if not underlying:
                 underlying = sym # Fallback
             
             doc = {
                "trade_id": trade_id,
                "symbol": sym,
                "underlying_symbol": underlying,
                "date_time": row.get("DateTime") or row.get("TradeDate"), 
                "quantity": float(row.get("Quantity") or 0),
                "price": float(row.get("TradePrice") or 0),
                "commission": float(row.get("IBCommission") or 0), # Check header... "IBExecID"? "Notes/Codes"?
                # The user dump has "NetCash", "TradePrice". Commission is usually separate or implied.
                # Actually user dump doesn't show "Commission" col in head -n 5 output.
                # It has "NetCash". NetCash = (Price * Qty) - Comm.
                # We can calculate commission = abs(NetCash - (Price * Qty))?
                # For now let's skip commission if missing.
                "realized_pnl": float(row.get("FifoPnlRealized") or 0),
                "buy_sell": row.get("Buy/Sell"),
                "order_type": row.get("OrderType") or "LMT", # Default/Unknown
                "exchange": row.get("Exchange") or "SMART"
            }
             db.ibkr_trades.update_one({"trade_id": trade_id}, {"$set": doc}, upsert=True)
             count += 1
        except ValueError:
            continue
            
    logging.info(f"Processed {count} trades.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", help="Path to Portfolio CSV")
    parser.add_argument("--trades", help="Path to Trades CSV")
    args = parser.parse_args()
    
    if args.portfolio:
        import_portfolio_csv(args.portfolio)
    if args.trades:
        import_trades_csv(args.trades)
