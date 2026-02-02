import logging
import sys
from app.config import settings
from pymongo import MongoClient

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_portfolio_rolls():
    try:
        # Override for local testing
        import os
        os.environ["MONGO_URI"] = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
        from app.config import settings
        settings.MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin" # Force override
        
        from app.services.roll_service import RollService
        print("Successfully imported RollService")
        
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # Get latest holdings
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        if not latest:
            print("No portfolio snapshot found.")
            return

        print(f"Using snapshot: {latest.get('snapshot_id') or latest.get('report_date')}")
        
        query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
        holdings = list(db.ibkr_holdings.find(query))
        
        # Filter for Options
        print(f"Total entries in snapshot: {len(holdings)}")
        if len(holdings) > 0:
             print("Searching for potential Options (Symbol len > 6)...")
             potential_opts = [h for h in holdings if len(h.get('symbol', '')) > 6]
             print(f"Found {len(potential_opts)} potential options via symbol length.")
             for h in potential_opts[:5]:
                 print(f"  {h.get('symbol')} | AssetClass: {h.get('asset_class')} | Qty: {h.get('quantity')}")
                 
        opts = [h for h in holdings if h.get("secType") in ["OPT", "FOP"] or h.get("asset_class") == "OPT"]

        # Check Trades
        print("-" * 10)
        trades = list(db.ibkr_trades.find().sort("date_time", -1).limit(5))
        print(f"Latest 5 Trades:")
        for t in trades:
            print(f"  {t.get('symbol')} | Buy/Sell: {t.get('buy_sell')} | Qty: {t.get('quantity')} | Price: {t.get('price')}")
            
        opts = [h for h in holdings if h.get("secType") in ["OPT", "FOP"] or h.get("asset_class") == "OPT"]

        opts = [h for h in holdings if h.get("secType") in ["OPT", "FOP"]] # OPT or FOP
        print(f"Found {len(opts)} options in portfolio.")
            
        print("-" * 20)
        print("Running RollService.analyze_portfolio_rolls...")
        
        service = RollService()
        suggestions = service.analyze_portfolio_rolls(holdings, max_days_to_expiration=14) # Check 14 days just in case
        
        print(f"Service returned {len(suggestions)} suggestions.")
        for s in suggestions:
            print(f"  {s['symbol']}: Score {s.get('score')} - {s.get('rationale')}")
            
    except ImportError as e:
        print(f"ImportError: {e}")
        sys.path.append('.')
        test_portfolio_rolls()
    except Exception as e:
        print(f"Runtime Error: {e}")

def test_parsing_logic():
    print("\ntesting IBKR CSV Parsing Logic for OCC Symbols...")
    
    # Mock CSV Line
    # Symbol, Quantity, AssetClass, ...
    # AMD   260206C00230000
    mock_row = {
        "Symbol": "AMD   260206C00230000",
        "Quantity": "-1",
        "AssetClass": "STK", # IBKR often mislabels generic assets if not configured? Or user said STK.
        "CostBasisPrice": "5.50",
        "MarkPrice": "4.20"
    }
    
    # Simulate DB Document creation (Copy-paste logic from ibkr_service.py roughly)
    doc = dict(mock_row)
    doc["symbol"] = mock_row["Symbol"]
    doc["quantity"] = float(mock_row["Quantity"])
    
    sym = doc["symbol"]
    # Logic from ibkr_service
    if len(sym) >= 21:
        try:
            root = sym[0:6].strip()
            date_str = sym[6:12]
            right = sym[12]
            strike_str = sym[13:]
            
            from datetime import datetime
            doc["secType"] = "OPT"
            doc["underlying_symbol"] = root
            doc["expiry"] = datetime.strptime(date_str, "%y%m%d").strftime("%Y-%m-%d")
            doc["strike"] = float(strike_str) / 1000.0
            doc["right"] = right
            print(f"Parsed Successfully: {doc['underlying_symbol']} {doc['expiry']} {doc['strike']} {doc['right']}")
        except Exception as e:
            print(f"Parse Error: {e}")

    # Now checks if logic matches what we expect
    if doc.get("secType") == "OPT" and doc.get("strike") == 230.0:
        print("PASS: Recognized as Option and parsed Strike 230.0")
    else:
        print("FAIL: Parsing failed.")
        
    return doc

if __name__ == "__main__":
    doc = test_parsing_logic()
    # test_portfolio_rolls() # Skip for now or run if needed
