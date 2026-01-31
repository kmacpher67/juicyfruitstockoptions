import csv
import io
from datetime import datetime
from collections import defaultdict
from pymongo import MongoClient
from app.config import settings

def generate_portfolio_csv_content() -> str:
    """
    Generates a CSV string of the USER's portfolio for 'ibkr'.
    Columns: Symbol, Trade Date, Purchase Price, Quantity
    Logic:
        - Aggregates by Underlying Symbol.
        - Prioritizes STK (Stocks):
            - If STK exists, IGNORE Options for that symbol.
            - Aggregates multiple accounts: Weighted Average Price, Sum of Quantity.
        - Fallback to OPT (Options):
            - Used only if no STK exists for the symbol.
            - Transformation: Quantity = Qty * 100, Price = Price * 100.
            - Aggregates multiple accounts.
    """
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # 1. Fetch Latest Holdings
        latest_holding = db.ibkr_holdings.find_one(sort=[("date", -1)])
        
        # Default header
        lines = ["Symbol,Trade Date,Purchase Price,Quantity"]

        if not latest_holding:
            return lines[0]
            
        latest_date = latest_holding.get("report_date")
        
        # Use snapshot_id if available to ensure atomic batch
        query = {"report_date": latest_date}
        if latest_holding.get("snapshot_id"):
            query = {"snapshot_id": latest_holding.get("snapshot_id")}
            
        holdings = list(db.ibkr_holdings.find(query))
        
        # 2. Group by Symbol
        # Map: Symbol -> { 'STK': [rows], 'OPT': [rows] }
        grouped = defaultdict(lambda: {'STK': [], 'OPT': []})
        
        for h in holdings:
            # Determine grouping symbol
            symbol = h.get("underlying_symbol")
            if not symbol:
                symbol = h.get("symbol")
            if not symbol:
                continue
                
            asset_class = h.get("asset_class", "STK") # Default to STK if missing?
            # Clean symbol
            symbol = str(symbol).strip()
            
            # Categorize
            if asset_class == "STK":
                grouped[symbol]['STK'].append(h)
            elif asset_class == "OPT":
                grouped[symbol]['OPT'].append(h)
            # Ignore others (FUT, CASH, etc) for now unless requested?
        
        # 3. Process Groups
        sorted_symbols = sorted(grouped.keys())
        
        for symbol in sorted_symbols:
            group = grouped[symbol]
            records_to_process = []
            is_option_mode = False
            
            # Prioritize STK
            if group['STK']:
                records_to_process = group['STK']
                is_option_mode = False
            elif group['OPT']:
                records_to_process = group['OPT']
                is_option_mode = True
            else:
                continue
                
            total_qty = 0.0
            total_cost_val = 0.0
            report_date_str = ""
            
            valid_records = False
            
            for h in records_to_process:
                # Quantity filter
                qty = h.get("quantity")
                if qty is None: 
                    qty = h.get("position") # fallback
                if qty is None:
                    continue
                
                qty = float(qty)
                
                # Price logic
                price = h.get("avg_cost")
                if price is None:
                    price = h.get("cost_basis")
                if price is None:
                    price = 0.0
                price = float(price)
                
                # Option Transformation
                if is_option_mode:
                    qty = qty * 100.0
                    price = price * 100.0
                    
                # Accumulate
                total_qty += qty
                total_cost_val += (qty * price)
                
                # Grab date from first valid record
                if not report_date_str:
                    d = h.get("report_date")
                    if d:
                        report_date_str = str(d).replace("-", "").replace("/", "")
                
                valid_records = True

            if not valid_records:
                continue
                
            # Calculate Weighted Avg
            avg_price = 0.0
            if total_qty != 0:
                avg_price = total_cost_val / total_qty
            else:
                # If net qty is 0, price is undefined/irrelevant? Or maybe 0?
                avg_price = 0.0
                
            # Write Row
            # Custom format: standard CSV (comma separated)
            # User Request: Quantity must be positive (importer assumes Long)
            final_qty = abs(total_qty)
            line = f"{symbol},{report_date_str},{avg_price:.2f},{int(final_qty) if final_qty.is_integer() else final_qty}"
            lines.append(line)
            
        return "\n".join(lines)

    except Exception as e:
        # Fail safe
        return "Symbol,\tTrade Date,\tPurchase Price,\tQuantity"
