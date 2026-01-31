import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient
from app.config import settings
from app.services.mappers import NavReportMapper
from app.models import NavReportType

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

def fetch_flex_report(query_id: str, token: str, label: str = "unknown", date_range: dict = None):
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
    # Add optional date overrides if the query supports dynamic dates? 
    # Not standard in all Flex Queries, but we try if requested.
    # Note: IBKR typically expects YYYYMMDD
    if date_range:
        if date_range.get("start"): params["startDate"] = date_range["start"]
        if date_range.get("end"): params["endDate"] = date_range["end"]
        logging.info(f"Applying Date Range: {params.get('startDate')} - {params.get('endDate')}")

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
    
    # Step 2: Download with Retry Logic
    logging.info(f"Downloading Statement {reference_code} (Label: {label})...")
    dl_params = {"t": token, "q": reference_code, "v": "3"}
    
    max_retries = 10
    retry_delay = 5 # seconds
    
    for attempt in range(max_retries):
        dl_resp = requests.get(FLEX_GET_URL, params=dl_params)
        
        if dl_resp.status_code != 200:
             # HTTP Error
             raise Exception(f"Failed to download statement ({dl_resp.status_code})")
             
        # Check for Async 1019 Error
        is_async_wait = False
        try:
            if dl_resp.content.strip().startswith(b"<"):
                root = ET.fromstring(dl_resp.content)
                if root.tag == "FlexStatementResponse":
                     err_code = root.find("ErrorCode")
                     if err_code is not None and err_code.text == "1019":
                         is_async_wait = True
                         logging.info(f"Report generation in progress (Attempt {attempt+1}/{max_retries}). Waiting {retry_delay}s...")
        except Exception:
            pass # Not an XML error, proceed
            
        if is_async_wait:
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay + 5, 20) # Backoff up to 20s
            continue
            
        # If we got here, it's either success or a different error/content.
        # Save validation happens by caller or explicit check?
        # Let's save debug and check for other errors (like invalid token) here to be safe, 
        # but re-using existing logic is cleaner.
        
        # Save Debug Info
        save_debug_file(label, dl_resp.content)
        
        # Verify it's not some other error
        if dl_resp.content.strip().startswith(b"<"):
            try:
                root = ET.fromstring(dl_resp.content)
                if root.tag == "FlexStatementResponse": # Step 2 Wrapper for Errors
                     err_code = root.find("ErrorCode")
                     err_msg = root.find("ErrorMessage")
                     if err_code is not None:
                         # Real Error (e.g. 1018 or others we can't retry easily)
                         raise Exception(f"IBKR Async Error {err_code.text}: {err_msg.text if err_msg is not None else 'Unknown'}")
            except ET.ParseError:
                pass 
                
        return dl_resp.content # Success
        
    raise Exception("IBKR Timeout: Report generation took too long.")


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

def run_ibkr_sync(check_interval_hours: float = 0.0, nav_days: int = 0):
    """
    Main entry point for Scheduler/API.
    check_interval_hours: Rate Limit check.
    nav_days: If > 0, requests specific date range for NAV query (Live/Short-term).
    """
    # 0. Rate Limit Check
    if check_interval_hours > 0:
        config = get_system_config()
        # Find 'ibkr_last_sync' directly from correct collection
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        last_sync_doc = db.system_config.find_one({"_id": "ibkr_last_sync"})
        
        if last_sync_doc and last_sync_doc.get("status") == "success":
            last_ts = last_sync_doc.get("timestamp")
            if last_ts:
                # Ensure offset-naive for comparison if Mongo returns naive
                age = datetime.utcnow() - last_ts
                if age.total_seconds() < (check_interval_hours * 3600):
                    logging.info(f"Skipping IBKR Sync: Data is fresh ({age.total_seconds()/60:.1f} min old). Threshold: {check_interval_hours}h.")
                    return "skipped"

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

        # 3. Sync NAV History
        if nav_days == 0:
            # Daily Scheduled Sync: Run ALL Reports completely
            
            # A. NAV Reports
            try:
                logging.info("Running Daily Comprehensive NAV Sync...")
                trigger_all_nav_reports()
            except Exception as e:
                msg = f"Full NAV Trigger Error: {e}"
                logging.exception(msg)
                errors.append(msg)
                
            # B. Holdings (Positions)
            q_holdings = config.get("query_id_pd_positions") or config.get("query_id_holdings")
            if q_holdings:
                 try:
                    logging.info("Fetching Daily Holdings...")
                    data_holdings = fetch_flex_report(q_holdings, token, label="holdings")
                    parse_and_store_holdings(data_holdings)
                 except Exception as e:
                    msg = f"Holdings Error: {e}"
                    logging.exception(msg)
                    errors.append(msg)
            
            # C. Trades
            q_trades = config.get("query_id_pd_trades") or config.get("query_id_trades")
            if q_trades:
                 try:
                    logging.info("Fetching Daily Trades...")
                    data_trades = fetch_flex_report(q_trades, token, label="trades")
                    parse_and_store_trades(data_trades)
                 except Exception as e:
                    msg = f"Trades Error: {e}"
                    logging.exception(msg)
                    errors.append(msg)
                    
        else:
             # On-Demand Legacy / Specific Day Logic (keeping for backward compatibility or specific API calls)
            q_nav = None
            nav_date_args = None 
            
            if nav_days == 1:
                q_nav = config.get("query_id_nav_1d") or config.get("query_id_nav")
            elif nav_days == 7:
                q_nav = config.get("query_id_nav_7d") or config.get("query_id_nav")
            elif nav_days == 30:
                q_nav = config.get("query_id_nav_30d") or config.get("query_id_nav")
            elif nav_days == 31: 
                q_nav = config.get("query_id_nav_mtd") or config.get("query_id_nav")
            elif nav_days == 365:
                q_nav = config.get("query_id_nav_1y") or config.get("query_id_nav")
            elif nav_days == 366:
                q_nav = config.get("query_id_nav_ytd") or config.get("query_id_nav")
            elif nav_days > 0:
                q_nav = config.get("query_id_nav")
                if q_nav:
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=nav_days)
                    nav_date_args = {"start": start_date.strftime("%Y%m%d"), "end": end_date.strftime("%Y%m%d")}
            
            if q_nav:
                try:
                    logging.info(f"Fetching NAV Data (Days={nav_days}) using Query {q_nav}...")
                    # Manual single fetch needs explicit report type if possible, or generic parse
                    # The parse_and_store_nav might need metadata if we drift from auto-trigger
                    # For legacy specific days, we just fetch and parse as generic or best effort
                    data = fetch_flex_report(q_nav, token, label="nav", date_range=nav_date_args)
                    parse_and_store_nav(data)
                except Exception as e:
                    msg = f"NAV Error: {e}"
                    logging.exception(msg)
                    errors.append(msg)
            else:
                 logging.warning(f"No NAV Query ID configured for {nav_days} days.")
                
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


def parse_and_store_nav(content, metadata: dict = None):
    """Dispatcher for NAV data."""
    if content.strip().startswith(b"<"):
        parse_xml_nav(content, metadata)
    else:
        parse_csv_nav(content.decode('utf-8', errors='ignore'), metadata)

def parse_csv_nav(csv_str, metadata: dict = None):
    """Parse IBKR NAV CSV."""
    import csv
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    lines = csv_str.splitlines()
    headers = None
    count = 0
    
    # Metadata extraction
    ibkr_type = metadata.get("ibkr_report_type") if metadata else None
    q_id = metadata.get("ibkr_query_id") if metadata else None
    q_name = metadata.get("ibkr_query_name") if metadata else None
    
    if isinstance(ibkr_type, str):
        try: ibkr_type = NavReportType(ibkr_type)
        except: ibkr_type = NavReportType.NAV_1D
    
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
        
        # Basic validation
        if not row.get("ClientAccountID"): continue
        
        try:
            # Use Mapper
            doc = NavReportMapper.map_to_mongo(
                raw_data=row,
                source_type="FLEX_CSV",
                ibkr_report_type=ibkr_type or NavReportType.NAV_1D,
                query_id=q_id,
                query_name=q_name
            )
            
            # Upsert
            db.ibkr_nav_history.update_one(
                {"account_id": doc["account_id"], "ibkr_report_type": doc["ibkr_report_type"], "_report_date": doc["_report_date"]},
                {"$set": doc},
                upsert=True
            )
            count += 1
            
        except Exception as e:
            logging.error(f"CSV Parse Error: {e}")
            continue
            
    logging.info(f"Processed {count} NAV records (CSV mapped).")

def parse_xml_nav(xml_content, metadata: dict = None):
    """
    Parse IBKR NAV XML.
    Uses NavReportMapper for consistent schema.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    root = ET.fromstring(xml_content)
    count = 0
    
    # Metadata context
    ibkr_type = metadata.get("ibkr_report_type") if metadata else None
    if isinstance(ibkr_type, str): # Verify enum or convert
        try:
            ibkr_type = NavReportType(ibkr_type)
        except:
            ibkr_type = NavReportType.NAV_1D # Fallback or error?
            
    q_id = metadata.get("ibkr_query_id") if metadata else None
    q_name = metadata.get("ibkr_query_name") if metadata else None

     # 1. Period Summary (ChangeInNAV) - Preferred for Flex Queries
    for node in root.findall(".//ChangeInNAV"):
        try:
            data = node.attrib
            acct = data.get("accountId")
            if not acct: continue
            
            # Use Mapper
            # XML Attributes need to be passed as raw_data
            # Validating if XML keys match what Mapper expects (Mapper has some aliases, but let's ensure)
            # Mapper expects: ClientAccountID/AccountId, EndingValue/NAV, etc.
            # XML keys: accountId, endingValue, fromDate, toDate, mtm, etc.
            # We map specific XML CamelCase to Mapper's expected keys if needed, OR Mapper handles them.
            # Mapper handles: AccountId, ToDate/ReportDate, EndingValue/NAV. 
            # Check keys: 'startingValue', 'endingValue', 'mtm', 'depositsWithdrawals', 'dividends', 'interest', 'changeInInterestAccruals', 'otherFees', 'commissions', 'TWR'
            
            # Normalize XML keys for Mapper (Capitalize first letter usually helps if Mapper expects PascalCase from CSV)
            # But the mapper.py uses .get("StartingValue") etc.
            # So we create a localized dict with PascalCase keys for the Mapper.
            
            def pascal(k): return k[0].upper() + k[1:] if k else k
            
            raw_mapped = {
                pascal(k): v for k, v in data.items()
            }
            # Fix specific overrides
            raw_mapped["ClientAccountID"] = data.get("accountId")
            raw_mapped["EndingValue"] = data.get("endingValue")
            raw_mapped["StartingValue"] = data.get("startingValue")
            raw_mapped["Mtm"] = data.get("mtm")
            raw_mapped["TWR"] = data.get("TWR")
            
            doc = NavReportMapper.map_to_mongo(
                raw_data=raw_mapped,
                source_type="FLEX_XML",
                ibkr_report_type=ibkr_type or NavReportType.NAV_1D, # Default if missing
                query_id=q_id,
                query_name=q_name
            )
            
            # Upsert
            db.ibkr_nav_history.update_one(
                {"account_id": doc["account_id"], "ibkr_report_type": doc["ibkr_report_type"], "_report_date": doc["_report_date"]},
                {"$set": doc},
                upsert=True
            )
            count += 1
            
        except Exception as e:
            logging.error(f"XML Nav Parse Error: {e}")
            continue

    logging.info(f"Processed {count} NAV records (XML mapped).")
                


from app.models import NavReportType

def get_nav_query_id(report_type: NavReportType, config: dict) -> str:
    """Map Enum to Config Field."""
    if report_type == NavReportType.NAV_1D: return config.get("query_id_nav_1d")
    if report_type == NavReportType.NAV_7D: return config.get("query_id_nav_7d")
    if report_type == NavReportType.NAV_30D: return config.get("query_id_nav_30d")
    if report_type == NavReportType.NAV_MTD: return config.get("query_id_nav_mtd")
    if report_type == NavReportType.NAV_YTD: return config.get("query_id_nav_ytd")
    if report_type == NavReportType.NAV_1Y: return config.get("query_id_nav_1y")
    return None

def fetch_and_store_nav_report(report_type: NavReportType):
    """
    On-Demand Sync for a specific NAV report.
    1. Lookup Query ID.
    2. Fetch XML/CSV.
    3. Save Raw.
    4. Parse & Update History.
    """
    save_sync_status("running", f"Fetching {report_type}...")
    logging.info(f"Starting On-Demand NAV Sync for {report_type}...")
    
    try:
        config = get_system_config()
        if not config or not config.get("flex_token"):
             raise Exception("No IBKR Token configured")
             
        token = config.get("flex_token")
        query_id = get_nav_query_id(report_type, config)
        
        if not query_id:
             raise Exception(f"No Query ID configured for {report_type}")
             
        # Fetch
        data = fetch_flex_report(query_id, token, label=f"nav_{report_type.lower()}")
        
        # Store & Parse
        # Metadata includes the Query Name (Report Type) for context
        meta = {
            "ibkr_report_type": report_type,
            "ibkr_query_id": query_id,
            "ibkr_query_name": report_type.value
        }
        parse_and_store_nav(data, metadata=meta)
        
        save_sync_status("success", f"Fetched {report_type}")
        return {"status": "success", "report": report_type}
        
    except Exception as e:
        save_sync_status("failed", f"Error {report_type}: {str(e)}")
        raise e

def trigger_all_nav_reports():
    """
    Triggers fetch for ALL configured NAV report types.
    Iterates through 'ibkr_config' and finds all keys starting with 'query_id_nav_'.
    """
    save_sync_status("running", "Triggering ALL NAV Reports...")
    logging.info("Starting Full NAV Schedule...")
    
    config = get_system_config()
    if not config:
        logging.error("No configuration found.")
        return
        
    # Map Config Keys to Report Types
    # config key -> NavReportType
    # query_id_nav_1d -> NAV_1D
    # query_id_nav_7d -> NAV_7D
    # etc.
    
    mapping = {
        "query_id_nav_1d": NavReportType.NAV_1D,
        "query_id_nav_7d": NavReportType.NAV_7D,
        "query_id_nav_30d": NavReportType.NAV_30D,
        "query_id_nav_mtd": NavReportType.NAV_MTD,
        "query_id_nav_ytd": NavReportType.NAV_YTD,
        "query_id_nav_1y": NavReportType.NAV_1Y
    }
    
    results = []
    
    for key, report_type in mapping.items():
        q_id = config.get(key)
        if q_id:
            # Simple Retry Loop for Rate Limits
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    logging.info(f"Triggering {report_type} (Query {q_id}) [Attempt {attempt+1}]...")
                    fetch_and_store_nav_report(report_type)
                    results.append(f"{report_type.value}: OK")
                    
                    # Success - Base Sleep
                    import time
                    time.sleep(10) 
                    break
                    
                except Exception as e:
                    err_str = str(e)
                    if "1018" in err_str or "Too many requests" in err_str:
                        if attempt < max_retries - 1:
                            wait_time = 60
                            logging.warning(f"Rate Limit Hit (1018). Waiting {wait_time}s before retry...")
                            save_sync_status("running", f"Rate Limit (1018) - Waiting {wait_time}s...")
                            import time
                            time.sleep(wait_time)
                            continue
                    
                    # If not 1018 or retries exhausted
                    msg = f"{report_type.value}: FAILED ({e})"
                    logging.error(msg)
                    results.append(msg)
                    break
        else:
            logging.warning(f"Skipping {report_type}: No Query ID configured.")
            
    save_sync_status("success", "Full NAV Schedule Completed: " + "; ".join(results))

