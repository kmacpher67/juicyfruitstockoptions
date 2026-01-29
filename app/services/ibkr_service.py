import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from pymongo import MongoClient
from app.config import settings

# IBKR Flex Web Service URL
# Using gdcdyn as requested (Global). Was ndcdyn (North America).
FLEX_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
FLEX_GET_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"

def get_system_config():
    """Fetch IBKR config from DB."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    return db.system_config.find_one({"_id": "ibkr_config"})

def save_debug_file(label: str, content: bytes):
    """Save raw response to disk for debugging."""
    try:
        import os
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Detect if XML or CSV
        ext = "xml"
        if content.strip().startswith(b"Date,"): # Simple CSV check
             ext = "csv"
        
        filename = f"app/ibkr_data/{label}/{timestamp}.{ext}"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "wb") as f:
            f.write(content)
            
        logging.info(f"Saved raw IBKR response to {filename}")
        
        # Log Logic (Truncate if too long)
        decoded = content.decode('utf-8', errors='ignore')
        logging.debug(f"Raw IBKR Response ({label}):\n{decoded[:2000]}...") # Log first 2000 chars
        
    except Exception as e:
        logging.error(f"Failed to save debug file: {e}")

def fetch_flex_report(query_id: str, token: str, label: str = "unknown"):
    """
    Two-step process:
    1. Send Request -> Get Reference Code
    2. Get Statement -> Download XML
    """
    if not query_id or not token:
        raise ValueError("Missing Query ID or Token")

    # Step 1: Initiate
    masked_token = f"{token[:4]}...{token[-4:]}"
    logging.info(f"Initiating Flex Query {query_id} (Token: {masked_token}) to {FLEX_URL}...")
    
    params = {"t": token, "q": query_id, "v": "3"}
    resp = requests.get(FLEX_URL, params=params)
    
    logging.debug(f"Step 1 Response Code: {resp.status_code}")
    logging.debug(f"Step 1 Payload: {resp.text}")
    
    if resp.status_code != 200:
        raise Exception(f"IBKR Init Failed ({resp.status_code}): {resp.text}")
        
    try:
        root = ET.fromstring(resp.content)
        status = root.find("Status").text
        
        if status != "Success":
            error_code = root.find("ErrorCode").text if root.find("ErrorCode") is not None else "Unknown"
            error_msg = root.find("ErrorMessage").text if root.find("ErrorMessage") is not None else "Unknown"
            raise Exception(f"IBKR API Error {error_code}: {error_msg}")
            
        reference_code = root.find("ReferenceCode").text
        
    except ET.ParseError:
        # If not XML, maybe it's an error string
        raise Exception(f"Failed to parse IBKR init response: {resp.text}")
    
    # Step 2: Download
    logging.info(f"Downloading Statement {reference_code} (Label: {label})...")
    dl_params = {"t": token, "q": reference_code, "v": "3"}
    dl_resp = requests.get(FLEX_GET_URL, params=dl_params)
    
    if dl_resp.status_code != 200:
        raise Exception(f"Failed to download statement ({dl_resp.status_code})")
        
    # Save Debug Info
    save_debug_file(label, dl_resp.content)
        
    return dl_resp.content # Bytes

def parse_csv_holdings(csv_str):
    """Parse IBKR Flex CSV for Holdings."""
    import csv
    import io
    
    # IBKR CSVs sometimes have pre-headers or blank lines.
    # We look for the header line starting with "Symbol" or similar.
    lines = csv_str.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if "Symbol" in line and "Quantity" in line:
            start_idx = i
            break
            
    reader = csv.DictReader(lines[start_idx:])
    positions = []
    
    for row in reader:
        # IBKR CSV keys might be quoted? DictReader handles standard CSV.
        # Map fields. keys are case sensitive based on CSV header.
        if not row.get("Symbol"): continue # Skip empty rows
        if row.get("Symbol") in ["EOS", "EOA", "EOF"]: continue # Skip IBKR End-of-Section markers
        
        try:
            doc = {
                "date": datetime.utcnow(),
                "report_date": datetime.utcnow().strftime("%Y-%m-%d"), # CSV doesn't always have report date in row
                "account_id": row.get("ClientAccountID") or row.get("AccountId"),
                "symbol": row.get("Symbol"),
                "underlying_symbol": row.get("UnderlyingSymbol") or row.get("Symbol"),
                "asset_class": row.get("AssetClass"),
                "quantity": float(row.get("Quantity", 0)),
                "cost_basis": float(row.get("CostBasisPrice", 0)),
                "market_price": float(row.get("MarkPrice", 0)),
                "market_value": float(row.get("PositionValue") or row.get("MarkValue", 0)),
                "percent_of_nav": float(row.get("PercentOfNAV", 0)) / 100.0, # XML usually gave 0.05, check if CSV gives 5.0?
                "unrealized_pnl": float(row.get("FifoPnlUnrealized", 0))
            }
            # Adjust percent if it looked like integer (e.g. 5.0 vs 0.05)
            # The Example User file shows "6.07" for 6%. So /100 is likely correct if we want 0.06
            if doc["percent_of_nav"] > 1.0: # If it was 6.07, dividing by 100 gives 0.0607.
                 # Actually in XML it was usually unit scale? Let's assume % for now.
                 pass
                 
            positions.append(doc)
        except ValueError:
            continue # Skip summary rows or malformed numbers

    if positions:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        # Store as discrete snapshot
        # Using the first record's ingestion time as the ID for the whole batch
        snapshot_id = positions[0]["date"]
        for p in positions:
            p["snapshot_id"] = snapshot_id
            
        db.ibkr_holdings.insert_many(positions)
        logging.info(f"Stored {len(positions)} holdings (CSV) in snapshot {snapshot_id}.")
    else:
        logging.warning("No positions found in CSV.")

def parse_and_store_holdings(content):
    """Dispatcher for XML or CSV."""
    if content.strip().startswith(b"<"):
        parse_xml_holdings(content)
    else:
        parse_csv_holdings(content.decode('utf-8', errors='ignore'))

def parse_xml_holdings(xml_content):
    """
    Parse 'Daily_Portfolio' XML and store snapshot.
    Expected Fields: Symbol, Quantity, CostBasis, ClosePrice, Value, etc.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    root = ET.fromstring(xml_content)
    # Structure depends on Flex Query Config. Assuming "OpenPositions" section.
    # We look for <OpenPositions> -> <OpenPosition ... />
    
    positions = []
    # Flex queries often wrap in FlexStatements -> FlexStatement -> OpenPositions
    for pos in root.findall(".//OpenPosition"):
        # Extract attributes handling various Flex XML schemas
        data = pos.attrib
        
        # Normalize Data
        doc = {
            "date": datetime.utcnow(), # Timestamp of ingestion
            "report_date": root.find(".//FlexStatement").attrib.get("date") if root.find(".//FlexStatement") is not None else datetime.utcnow().strftime("%Y-%m-%d"),
            "account_id": data.get("accountId"),
            "symbol": data.get("symbol"),
            "quantity": float(data.get("position", 0)),
            "cost_basis": float(data.get("costBasisPrice", 0)),
            "market_price": float(data.get("markPrice", 0)),
            "market_value": float(data.get("markValue", 0)),
            "percent_of_nav": float(data.get("percentOfNAV", 0)) if data.get("percentOfNAV") else 0.0,
            "unrealized_pnl": float(data.get("fifoPnlUnrealized", 0))
        }
        positions.append(doc)

    if positions:
        # Store as discrete snapshot
        snapshot_id = positions[0]["date"]
        for p in positions:
            p["snapshot_id"] = snapshot_id
            
        db.ibkr_holdings.insert_many(positions)
        logging.info(f"Stored {len(positions)} holding records in snapshot {snapshot_id}.")
    else:
        logging.warning("No positions found in Flex XML.")

def parse_csv_trades(csv_str):
    """Parse IBKR Flex CSV for Trades."""
    import csv
    
    lines = csv_str.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if "Symbol" in line and "Buy/Sell" in line: # Header identification
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
             doc = {
                "trade_id": trade_id,
                "symbol": row.get("Symbol"),
                "underlying_symbol": row.get("UnderlyingSymbol") or row.get("Symbol"),
                "date_time": row.get("DateTime"),
                "quantity": float(row.get("Quantity", 0)),
                "price": float(row.get("TradePrice", 0)),
                "commission": float(row.get("IBCommission", 0)),
                "realized_pnl": float(row.get("FifoPnlRealized") or row.get("RealizedPnL") or 0),
                "buy_sell": row.get("Buy/Sell"), # CSV key might differ
                "order_type": row.get("OrderType"),
                "exchange": row.get("Exchange")
            }
             db.ibkr_trades.update_one({"trade_id": trade_id}, {"$set": doc}, upsert=True)
             count += 1
        except ValueError:
            continue
            
    logging.info(f"Processed {count} trades (CSV).")

def parse_and_store_trades(content):
    """Dispatcher."""
    if content.strip().startswith(b"<"):
        parse_xml_trades(content)
    else:
        parse_csv_trades(content.decode('utf-8', errors='ignore'))

def parse_xml_trades(xml_content):
    """
    Parse 'Recent_Trades' XML and store idempotently.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    root = ET.fromstring(xml_content)
    trades_count = 0
    
    for trade in root.findall(".//Trade"):
        data = trade.attrib
        
        # Unique ID is critical for idempotency
        # IBKR usually provides 'tradeID' or 'transactionID'
        trade_id = data.get("tradeID") or data.get("transactionID")
        
        if not trade_id:
            continue
            
        doc = {
            "trade_id": trade_id,
            "symbol": data.get("symbol"),
            "date_time": data.get("dateTime"), # Parse strictly if needed
            "quantity": float(data.get("quantity", 0)),
            "price": float(data.get("tradePrice", 0)),
            "commission": float(data.get("ibCommission", 0)),
            "buy_sell": data.get("buySell"),
            "order_type": data.get("orderType"),
            "exchange": data.get("exchange")
        }
        
        # Upsert: If trade_id exists, update it (or ignore). 
        # Using upsert ensures we don't duplicate.
        db.ibkr_trades.update_one(
            {"trade_id": trade_id},
            {"$set": doc},
            upsert=True
        )
        trades_count += 1
        
    logging.info(f"Processed {trades_count} trades.")

def save_sync_status(status: str, message: str):
    """Persist the result of the sync job."""
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        db.ibkr_status_log.insert_one({
            "timestamp": datetime.utcnow(),
            "status": status, # 'running', 'success', 'failed'
            "message": message
        })
        # Also update a 'latest' pointer for quick UI lookup
        db.system_config.update_one(
            {"_id": "ibkr_last_sync"},
            {"$set": {
                "timestamp": datetime.utcnow(),
                "status": status,
                "message": message
            }},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Failed to save sync status: {e}")

def run_ibkr_sync():
    """Main entry point for Scheduler/API."""
    save_sync_status("running", "Sync Started")
    logging.info("Starting IBKR Sync...")
    
    errors = []
    
    try:
        config = get_system_config()
        if not config or not config.get("flex_token"):
            msg = "IBKR Sync Aborted: No config/token."
            logging.warning(msg)
            save_sync_status("failed", msg)
            return
            
        token = config.get("flex_token")
        
        # 1. Sync Holdings
        q_holdings = config.get("query_id_holdings")
        if q_holdings:
            try:
                data = fetch_flex_report(q_holdings, token, label="portfolio")
                parse_and_store_holdings(data)
            except Exception as e:
                msg = f"Holdings Error: {e}"
                logging.exception(msg)
                errors.append(msg)
                
        # 2. Sync Trades
        q_trades = config.get("query_id_trades")
        if q_trades:
            try:
                data = fetch_flex_report(q_trades, token, label="trades")
                parse_and_store_trades(data)
            except Exception as e:
                msg = f"Trades Error: {e}"
                logging.exception(msg)
                errors.append(msg)

        # 3. Sync NAV History
        q_nav = config.get("query_id_nav")
        if q_nav:
            try:
                data = fetch_flex_report(q_nav, token, label="nav")
                parse_and_store_nav(data)
            except Exception as e:
                msg = f"NAV Error: {e}"
                logging.exception(msg)
                errors.append(msg)
                
        # 4. Trigger AI Analysis
        try:
            from app.services.portfolio_analysis import run_portfolio_analysis
            run_portfolio_analysis()
        except Exception as e:
            msg = f"Analysis Error: {e}"
            logging.exception(msg)
            errors.append(msg)
        
        # Determine Status
        if not errors:
            save_sync_status("success", "Sync & Analysis Complete")
            logging.info("IBKR Sync Completed Successfully.")
        else:
            # Partial or Full Failure
            status = "failed" if len(errors) >= 2 else "warning"
            save_sync_status(status, "; ".join(errors))
    except Exception as e:
        logging.exception(f"IBKR Sync Critical Failure: {e}")
        save_sync_status("failed", f"Critical Error: {str(e)}")


def parse_and_store_nav(content):
    """Dispatcher for NAV data."""
    if content.strip().startswith(b"<"):
        parse_xml_nav(content)
    else:
        parse_csv_nav(content.decode('utf-8', errors='ignore'))

def parse_csv_nav(csv_str):
    """Parse IBKR NAV CSV."""
    import csv
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    lines = csv_str.splitlines()
    headers = None
    count = 0
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Identify Header
        if "ClientAccountID" in line and "EndingValue" in line:
            reader = csv.reader([line])
            headers = next(reader)
            continue
            
        if not headers: continue
        
        # Parse Row
        reader = csv.reader([line])
        try:
             row_values = next(reader)
        except StopIteration: continue
        
        if len(row_values) != len(headers): continue
        
        row = dict(zip(headers, row_values))
        acct = row.get("ClientAccountID")
        val = row.get("EndingValue")
        date_raw = row.get("ToDate") # "20251231" usually
        
        if not (acct and val and date_raw): continue
        
        try:
            # IBKR Date Format in CSV often YYYYMMDD
            if len(date_raw) == 8:
                date_iso = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
            else:
                # Or standard YYYY-MM-DD
                date_iso = date_raw
                
            doc = {
                "account_id": acct,
                "report_date": date_iso,
                "total_nav": float(val),
                "currency": row.get("CurrencyPrimary", "USD"),
                "source": "FLEX_CSV",
                "ingested_at": datetime.utcnow()
            }
            
            db.ibkr_nav_history.update_one(
                {"account_id": acct, "report_date": date_iso},
                {"$set": doc},
                upsert=True
            )
            count += 1
        except Exception:
            continue
            
    logging.info(f"Processed {count} NAV records (CSV).")

def parse_xml_nav(xml_content):
    """Parse IBKR NAV XML."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    root = ET.fromstring(xml_content)
    count = 0
    # Schema varies, typically FlexStatement -> EquitySummaryByReportDateInBase
    # Or just look for generic Equity Summary structure
    
    # Try finding EquitySummaryByReportDateInBase
    for node in root.findall(".//EquitySummaryByReportDateInBase"):
        data = node.attrib
        try:
            acct = data.get("accountId")
            val = data.get("endingValue") or data.get("total")
            date_raw = data.get("date") or data.get("reportDate") # 20251231?
            
            if not (acct and val and date_raw): continue
            
            # Date Parsing
            if len(date_raw) == 8 and date_raw.isdigit():
                 date_iso = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
            else:
                 date_iso = date_raw
                 
            doc = {
                "account_id": acct,
                "report_date": date_iso,
                "total_nav": float(val),
                "currency": data.get("currency", "USD"),
                "source": "FLEX_XML",
                "ingested_at": datetime.utcnow()
            }
            
            db.ibkr_nav_history.update_one(
                {"account_id": acct, "report_date": date_iso},
                {"$set": doc},
                upsert=True
            )
            count += 1
        except Exception:
            continue
            
    logging.info(f"Processed {count} NAV records (XML).")
                

