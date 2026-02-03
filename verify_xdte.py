from pymongo import MongoClient
import pandas as pd
from datetime import datetime
from app.config import settings

def verify_xdte():
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")

    account = "U110638"
    
    # 1. Check Holdings
    print(f"\n--- Verifying Holdings for {account} (querying account_id) ---")
    
    # Get latest snapshot ID
    latest_holding = db.ibkr_holdings.find_one({"account_id": account}, sort=[("date", -1)])
    if not latest_holding:
        print(f"No holdings found for account_id {account}")
        
        # Debug: List available account_ids
        print(f"Available Account IDs: {db.ibkr_holdings.distinct('account_id')}")
        return

    snapshot_id = latest_holding.get("snapshot_id")
    report_date = latest_holding.get("report_date")
    print(f"Latest Snapshot: {snapshot_id or report_date}")
    
    query = {"account_id": account}
    if snapshot_id:
        query["snapshot_id"] = snapshot_id
    elif report_date:
        query["report_date"] = report_date
        
    holdings = list(db.ibkr_holdings.find(query))
    print(f"Total Holdings: {len(holdings)}")
    
    # Filter for Short Options < 7 DTE
    short_ops_7dte = []
    now = datetime.utcnow()
    
    for h in holdings:
        # Check type
        sec_type = h.get("secType") or h.get("asset_class")
        if sec_type not in ["OPT", "FOP"]:
            continue
            
        # Check Short
        qty = float(h.get("quantity", 0))
        if qty >= 0:
            continue
            
        # Check Expiry
        exp_str = h.get("expiry")
        if not exp_str:
            continue
            
        try:
             # Normalize Date
            if len(exp_str) == 8 and "-" not in exp_str:
                 exp_dt = datetime.strptime(exp_str, "%Y%m%d")
            else:
                 exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            
            days = (exp_dt - now).days
            
            # Debug: Print all short ops
            print(f"DEBUG: Found Short {h.get('symbol')} {exp_str} (DTE: {days})")
            
            if days <= 7:
                h['days_to_exp'] = days
                short_ops_7dte.append(h)
        except Exception as e:
            print(f"Error parsing date {exp_str}: {e}")
            
    print(f"Found {len(short_ops_7dte)} Short Options <= 7 DTE:")
    for op in short_ops_7dte:
        print(f" - {op.get('symbol')} {op.get('expiry')} {op.get('strike')} (Qty: {op.get('quantity')}, DTE: {op.get('days_to_exp')})")


    # 2. Check Opportunities
    print(f"\n--- Verifying Opportunities (Source: ExpirationScanner) ---")
    
    # We don't strictly link opps to accounts yet in the schema (maybe?), but we can check by symbol
    # or if we added context.
    
    opps = list(db.opportunities.find({"trigger_source": "ExpirationScanner"}))
    print(f"Total ExpirationScanner Opportunities: {len(opps)}")
    
    for op in opps:
        # Check if it matches our 7DTE list
        matching_holding = next((h for h in short_ops_7dte if h.get('symbol') == op.get('symbol')), None)
        status = "MATCH" if matching_holding else "ORPHAN/OTHER ACC"
        print(f" - {op.get('symbol')}: {op.get('proposal', {}).get('expiry')} (Status: {status})")

if __name__ == "__main__":
    verify_xdte()
