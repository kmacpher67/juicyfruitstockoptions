from datetime import timedelta, datetime
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import MongoClient
import yfinance as yf
import pandas as pd

from app.auth.dependencies import get_current_active_user
from app.auth.utils import create_access_token, verify_password, get_password_hash
from app.config import settings
from app.models import Token, User, StockRecord, IBKRConfig, IBKRStatus, NavReportType
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import fetch_and_store_nav_report
from app.database import get_db
from app.services.signal_service import SignalService
from app.utils.logging_config import log_endpoint

router = APIRouter()


import logging
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
@log_endpoint
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Authenticate against MongoDB
    logger.debug(f"Login attempt for user: {form_data.username}")
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    try:
        user = db.users.find_one({"username": form_data.username})
        
        if not user:
             logger.warning(f"Login failed: User {form_data.username} not found")
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not verify_password(form_data.password, user["hashed_password"]):
             logger.warning(f"Login failed: Password mismatch for {form_data.username}")
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login DB error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Login Error")

@router.get("/users/me", response_model=User)
@log_endpoint
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

# --- Secured Endpoints ---

@router.get("/stocks", response_model=List[StockRecord])
@log_endpoint
async def get_stocks(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Fetch all stock records from MongoDB.
    """
    try:
        # Connect to Mongo (Connection pooling is handled by driver, simple connect here is fine for now)
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        collection = db["stock_data"]
        
        # Fetch all records, exclude internal Mongo ID
        cursor = collection.find({}, {"_id": 0})
        results = list(cursor)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/run/portfolio-fixer")
@log_endpoint
def run_portfolio_fixer_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return run_portfolio_fixer()

from fastapi import BackgroundTasks
from app.jobs import create_job, get_job, update_job_status, JobStatus, Job

def background_job_wrapper(job_id: str, func):
    """Wrapper to run a function and update job status."""
    try:
        update_job_status(job_id, JobStatus.RUNNING)
        result = func()
        update_job_status(job_id, JobStatus.COMPLETED, result=result)
    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, error=str(e))

@router.get("/jobs/{job_id}", response_model=Job)
@log_endpoint
def get_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    job = get_job(job_id)
    if not job:
          raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/run/stock-live-comparison")
@log_endpoint
def run_stock_live_comparison_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # Create Job
    job = create_job()
    
    # Add to Background Tasks
    background_tasks.add_task(background_job_wrapper, job.id, run_stock_live_comparison)
    
    # Add to Background Tasks
    background_tasks.add_task(background_job_wrapper, job.id, run_stock_live_comparison)
    
    return {"job_id": job.id, "status": "queued"}

# --- Scheduler Config Endpoints ---

from pydantic import BaseModel
class ScheduleConfig(BaseModel):
    hour: int
    minute: int

@router.get("/schedule", response_model=ScheduleConfig)
@log_endpoint
def get_schedule(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    from app.scheduler.jobs import get_schedule_config
    return get_schedule_config()

@router.post("/schedule")
@log_endpoint
def update_schedule(
    config: ScheduleConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    from app.scheduler.jobs import reschedule_daily_job
    try:
        reschedule_daily_job(config.hour, config.minute)
        return {"status": "success", "message": f"Rescheduled to {config.hour:02d}:{config.minute:02d}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- User Settings Persistence ---

class UserSettings(BaseModel):
    pageSize: int = 100
    sortColumn: str = "Ticker"
    sortOrder: str = "asc"

@router.get("/settings", response_model=UserSettings)
@log_endpoint
def get_user_settings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        # Fetch settings for this user
        doc = db.user_settings.find_one({"username": current_user.username})
        if doc:
            return UserSettings(**doc)
        # Defaults
        return UserSettings()
    except Exception as e:
        # Default fallback on error
        return UserSettings()

@router.post("/settings")
@log_endpoint
def save_user_settings(
    user_settings: UserSettings,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        db.user_settings.update_one(
            {"username": current_user.username},
            {"$set": user_settings.dict()},
            upsert=True
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

class AccountConfig(BaseModel):
    account_id: str
    taxable: bool = False
    alias: str = ""

@router.get("/settings/accounts", response_model=List[AccountConfig])
@log_endpoint
def get_account_settings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """List all known accounts and their settings."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Discover Accounts from Holdings & NAV
    # Use distinct to find all account IDs present in data
    known_accounts = set(db.ibkr_holdings.distinct("account_id"))
    known_accounts.update(db.ibkr_nav_history.distinct("account_id"))
    
    # 2. Fetch Metadata
    meta_doc = db.system_config.find_one({"_id": "account_metadata"}) or {}
    meta = meta_doc.get("accounts", {})
    
    results = []
    for acc in sorted([a for a in known_accounts if a]): # Filter None
        cfg = meta.get(acc, {})
        results.append(AccountConfig(
            account_id=acc,
            taxable=cfg.get("taxable", False),
            alias=cfg.get("alias", "")
        ))
        
    return results

@router.post("/settings/accounts")
@log_endpoint
def update_account_settings(
    configs: List[AccountConfig],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")
         
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Convert list to dict map for storage
    meta_map = {c.account_id: {"taxable": c.taxable, "alias": c.alias} for c in configs}
    
    db.system_config.update_one(
        {"_id": "account_metadata"},
        {"$set": {"accounts": meta_map}},
        upsert=True
    )
    return {"status": "success"}

@router.get("/reports", response_model=List[str])
@log_endpoint
async def list_reports(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """List all available Excel reports."""
    import os
    report_dir = "report-results"
    if not os.path.exists(report_dir):
        return []
    files = [f for f in os.listdir(report_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(report_dir, x)), reverse=True)
    return files

@router.get("/reports/{filename}/data")
@log_endpoint
async def get_report_data(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Read a specific Excel file and return as JSON for the grid."""
    import os
    import pandas as pd
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        # Read Excel using pandas
        # Ensure we read the correct engine
        df = pd.read_excel(report_path, engine='openpyxl')
        
        # Handle NaN/Inf for JSON compliance
        df = df.replace({float('nan'): None, float('inf'): None, float('-inf'): None})
        
        # Convert to list of dicts
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {str(e)}")

@router.get("/reports/{filename}/download")
@log_endpoint
async def download_report(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Download a specific Excel report."""
    import os
    from fastapi.responses import FileResponse
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(report_path, filename=filename)

# --- IBKR Integrations (Admin Only) ---

@router.get("/integrations/ibkr", response_model=IBKRStatus)
@log_endpoint
def get_ibkr_status(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    config = db.system_config.find_one({"_id": "ibkr_config"})
    
    if not config:
        return IBKRStatus(configured=False)
        
    token = config.get("flex_token", "")
    masked = f"{token[:4]}...{token[-4:]}" if token and len(token) > 8 else "****"
    
    last_sync_doc = db.system_config.find_one({"_id": "ibkr_last_sync"})
    last_sync = None
    if last_sync_doc:
        last_sync = {
            "status": last_sync_doc.get("status"),
            "message": last_sync_doc.get("message"),
            "timestamp": last_sync_doc.get("timestamp")
        }
    
    return IBKRStatus(
        configured=True,
        flex_token_masked=masked,
        query_id_holdings=config.get("query_id_holdings"),
        query_id_trades=config.get("query_id_trades"),
        query_id_nav=config.get("query_id_nav"),
        query_id_nav_1d=config.get("query_id_nav_1d"),
        query_id_nav_7d=config.get("query_id_nav_7d"),
        query_id_nav_30d=config.get("query_id_nav_30d"),
        query_id_nav_mtd=config.get("query_id_nav_mtd"),
        query_id_nav_ytd=config.get("query_id_nav_ytd"),
        query_id_nav_1y=config.get("query_id_nav_1y"),
        query_id_dividends=config.get("query_id_dividends"),
        last_sync=last_sync
    )

@router.post("/integrations/ibkr")
@log_endpoint
def update_ibkr_config(
    config: IBKRConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    update_data = {}
    if config.flex_token:
        update_data["flex_token"] = config.flex_token
    if config.query_id_holdings:
        update_data["query_id_holdings"] = config.query_id_holdings
    if config.query_id_trades:
        update_data["query_id_trades"] = config.query_id_trades
    if config.query_id_nav:
        update_data["query_id_nav"] = config.query_id_nav
    if config.query_id_nav_1d: update_data["query_id_nav_1d"] = config.query_id_nav_1d
    if config.query_id_nav_7d: update_data["query_id_nav_7d"] = config.query_id_nav_7d
    if config.query_id_nav_30d: update_data["query_id_nav_30d"] = config.query_id_nav_30d
    if config.query_id_nav_mtd: update_data["query_id_nav_mtd"] = config.query_id_nav_mtd
    if config.query_id_nav_ytd: update_data["query_id_nav_ytd"] = config.query_id_nav_ytd
    if config.query_id_nav_1y: update_data["query_id_nav_1y"] = config.query_id_nav_1y
    if config.query_id_dividends: update_data["query_id_dividends"] = config.query_id_dividends
        
    db.system_config.update_one(
        {"_id": "ibkr_config"},
        {"$set": update_data},
        upsert=True
    )
    return {"status": "success"}

@router.post("/integrations/ibkr/test")
@log_endpoint
def test_ibkr_connection(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    config = db.system_config.find_one({"_id": "ibkr_config"})
    
    if not config or not config.get("flex_token"):
        return {"success": False, "message": "No token configured."}
        
    return {"success": True, "message": "Token found (Dry Run Verification)"}

from fastapi import BackgroundTasks
from app.services.ibkr_service import run_ibkr_sync

@router.post("/integrations/ibkr/sync")
@log_endpoint
async def sync_ibkr_data(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    stale_hours: float = 0.0,
    nav_days: int = 0
):
    """
    Trigger manual sync of IBKR Portfolio and Trades.
    stale_hours: If > 0, skips if data is fresher than this (Auto-Sync).
    nav_days: If > 0, requests specific N-day report for NAV (Live).
    """
    if current_user.role != "admin": # Or 'portfolio' role? For now Admin.
        raise HTTPException(status_code=403, detail="Not authorized")
        
    background_tasks.add_task(run_ibkr_sync, stale_hours, nav_days)
    return {"status": "queued", "message": "IBKR Sync started in background."}

@router.post("/integrations/ibkr/sync/nav-all")
@log_endpoint
async def sync_all_nav_reports(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Trigger comprehensive sync of ALL configured NAV reports (1D, 7D, 30D, MTD, etc).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    from app.services.ibkr_service import trigger_all_nav_reports
    background_tasks.add_task(trigger_all_nav_reports)
    return {"status": "queued", "message": "Full NAV Schedule triggered."}

@router.get("/portfolio/stats")
@log_endpoint
async def get_portfolio_stats(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get calculated NAV stats (Current, 30d, YTD, etc)."""
    # Helper to protect View
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    from app.services.portfolio_analysis import get_nav_history_stats
    return get_nav_history_stats()

@router.get("/nav/report/{report_type}")
@log_endpoint
def get_nav_report_endpoint(
    report_type: NavReportType,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get generic NAV report data.
    If data for today is missing for this specific report type, trigger async fetch.
    Returns status='fetching' (202) if triggered, or status='available' with data if present.
    """
    # 1. Check if we have stats
    from app.services.portfolio_analysis import get_report_stats
    stats_data = get_report_stats(report_type)
    
    if stats_data:
        return {
            "status": "available",
            "stats": stats_data
        }
        
    # 2. If not found, Trigger Fetch
    # Only if truly missing from DB.
    # Note: validation of "freshness" is handled by the user pressing the button again? 
    # Or should we enforce "today"?
    # The user said "simple single call". If old data is there, give it?
    # Assuming "get_report_stats" returns the LATEST available.
    if not stats_data:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        recent_entry = db.ibkr_raw_flex_reports.find_one({
            "ibkr_report_type": report_type,
            # We can check date if we want strict freshness
        })
        # If we have raw report but parsing failed? Unlikely.
        
        # Trigger background fetch if absolutely nothing found
        background_tasks.add_task(fetch_and_store_nav_report, report_type)
        return {"status": "fetching", "message": f"Report {report_type} requested."}
    
    return {"status": "error", "message": "Unknown state"}

@router.get("/portfolio/holdings")
@log_endpoint
async def get_portfolio_holdings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get latest snapshot of holdings."""
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Find latest date
    # Find latest snapshot
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    # Use unique snapshot_id to avoid duplicates from multiple syncs in one day
    snapshot_id = latest.get("snapshot_id")
    if snapshot_id:
        query = {"snapshot_id": snapshot_id}
    else:
        # Fallback for legacy data
        query = {"report_date": latest.get("report_date")}
        
    data = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    # Enrich with Dividend History
    symbols = list(set([h["symbol"] for h in data if "symbol" in h]))
    if symbols:
        pipeline = [
            {"$match": {"symbol": {"$in": symbols}, "code": "RE"}},
            {"$group": {"_id": "$symbol", "total_divs": {"$sum": "$net_amount"}}}
        ]
        div_sums = {doc["_id"]: doc["total_divs"] for doc in db.ibkr_dividends.aggregate(pipeline)}
        
        for row in data:
            sym = row.get("symbol")
            if not sym: continue
            
            divs = div_sums.get(sym, 0.0)
            row["divs_earned"] = divs
            
            unrealized = row.get("unrealized_pnl", 0)
            row["total_return"] = unrealized + divs
            
            cb = row.get("cost_basis", 0)
            if cb > 0:
                row["true_yield"] = divs / cb
            else:
                row["true_yield"] = 0.0

    # 3. Enhanced Metrics (Coverage, DTE, ITM/OTM)
    from app.services.options_analysis import OptionsAnalyzer
    analyzer = OptionsAnalyzer(data)
    grouped = analyzer.grouped
    now = datetime.now()

    for row in data:
        # A. Coverage Status
        und = row.get("underlying_symbol") or row.get("underlying") or row.get("symbol")
        stats = grouped.get(und)
        if stats:
            shares = stats["shares"]
            covered = stats["short_calls"]
            if shares > 0:
                if covered >= shares:
                    row["coverage_status"] = "Covered"
                elif covered > 0:
                    row["coverage_status"] = "Partial"
                else:
                    row["coverage_status"] = "Uncovered"
            elif covered > 0:
                row["coverage_status"] = "Naked"
            else:
                row["coverage_status"] = "N/A"

        # B. Option Metrics
        sec_type = row.get("asset_class") or row.get("secType")
        if sec_type in ["OPT", "FOP"]:
            # Parse Expiry & DTE
            exp_str = row.get("expiry")
            if exp_str:
                try:
                    if len(exp_str) == 8 and "-" not in exp_str:
                         exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                    else:
                         exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                    
                    dte = (exp_dt.date() - now.date()).days
                    row["dte"] = dte
                    row["is_expiring_soon"] = dte <= 6
                except:
                    pass
            
            # Strike Distance & ITM
            strike = float(row.get("strike", 0))
            price = float(row.get("market_price", 0) or row.get("mark_price", 0) or 0)
            if strike > 0 and price > 0:
                row["dist_to_strike_pct"] = abs(price - strike) / strike
                
                # ITM Check using OSI symbol (AAPL  250117C00150000)
                # re is already imported in routes.py (line 34 in options_analysis, but I need it here)
                # But I can just check for 'C' or 'P' after the date.
                sym = row.get("symbol", "")
                import re
                if re.search(r'\d{6}C\d+', sym):
                    row["is_itm"] = price >= strike
                elif re.search(r'\d{6}P\d+', sym):
                    row["is_itm"] = price <= strike
                else:
                    row["is_itm"] = False

    return data

@router.get("/portfolio/alerts")
@log_endpoint
async def get_portfolio_alerts(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Run Advanced Options Analysis on current holdings.
    Returns list of Alert objects (Uncovered, Naked, Profit).
    """
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Fetch Latest Holdings (Snapshot)
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    snapshot_id = latest.get("snapshot_id")
    if snapshot_id:
        query = {"snapshot_id": snapshot_id}
    else:
        query = {"report_date": latest.get("report_date")}
        
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    # 2. Fetch Market Data for Context
    # We want a map {Symbol: StockDataDict}
    # Optimize: Only fetch for symbols in holdings? Or just fetch all (dataset is small enough).
    stock_cursor = db.stock_data.find({}, {"_id": 0})
    market_data = {item["Ticker"]: item for item in stock_cursor}
    
    # 3. Analyze
    from app.services.options_analysis import OptionsAnalyzer
    analyzer = OptionsAnalyzer(holdings, market_data=market_data)
    
    alerts = []
    alerts.extend(analyzer.analyze_naked())    # Critical
    alerts.extend(analyzer.analyze_coverage()) # Opportunity (Filtered by Trend)
    alerts.extend(analyzer.analyze_profit())   # Actionable
    
    return alerts

class ScannerConfig(BaseModel):
    preset: str = None # "momentum", "juicy", or None for custom (future)
    criteria: dict = None
    persist: bool = False

@router.post("/analysis/scan")
@log_endpoint
def run_stock_scanner(
    config: ScannerConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Run a stock scan based on a preset or criteria.
    Presets: 'momentum', 'juicy'
    """
    from app.services.scanner_service import scan_momentum_calls, scan_juicy_candidates, run_scanner
    
    if config.preset == "momentum":
        return scan_momentum_calls(persist=config.persist)
    elif config.preset == "juicy":
        return scan_juicy_candidates(persist=config.persist)
    elif config.criteria:
        # Advanced: Pass raw criteria (Sanitize/Limit in service recommended)
        return run_scanner(config.criteria, persist=config.persist)
    else:
         raise HTTPException(status_code=400, detail="Must provide preset or criteria")


class RollInput(BaseModel):
    symbol: str
    strike: float
    expiration: str # YYYY-MM-DD
    position_type: str = "call" # call/put

@router.post("/analysis/roll")
@log_endpoint
def analyze_rolls(
    input: RollInput,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Analyze potential rolls for an options position.
    Uses real-time data from Yahoo Finance.
    """
    from app.services.roll_service import RollService
    service = RollService()
    result = service.find_rolls(
        symbol=input.symbol,
        current_strike=input.strike,
        current_exp_date=input.expiration,
        position_type=input.position_type
    )
    
    if "error" in result:
         raise HTTPException(status_code=400, detail=result["error"])
         
    return result

# --- Ticker & Opportunity Analysis ---
@router.get("/analysis/rolls")
@log_endpoint
def analyze_smart_rolls(
    current_user: Annotated[User, Depends(get_current_active_user)],
    persist: bool = False
):
    """
    Scan the USER's portfolio for Short Calls expiring soon (default 10 days)
    and find Smart Roll opportunities (Up & Out, Credit, Short Duration).
    """
    # 1. Fetch Portfolio
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Get latest holdings
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    if not holdings:
        return []
        
    # 2. Analyze
    from app.services.roll_service import RollService
    service = RollService()
    
    # Analyze
    # Analyze
    suggestions = service.analyze_portfolio_rolls(holdings, max_days_to_expiration=10, persist=persist)
    
    return suggestions


@router.get("/analysis/rolls/{ticker}")
@log_endpoint
def analyze_ticker_smart_rolls(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get Smart Roll opportunities for a specific ticker's held options.
    Flattened list for TickerModal consumption.
    """
    ticker = ticker.upper().strip()
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Get latest holdings
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
    # Filter by symbol in query to save bandwidth
    query["symbol"] = ticker
    
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    if not holdings:
        return []
        
    from app.services.roll_service import RollService
    service = RollService()
    
    # We use analyze_portfolio_rolls logic but specifically for this list
    suggestions = service.analyze_portfolio_rolls(holdings, max_days_to_expiration=45) # Allow wider window for specific analysis
    
    # Flatten: TickerModal expects a list of rolls.
    # But wait, TickerModal might expect the 'Candidate' objects directly?
    # Each suggestion in 'suggestions' has 'rolls': [Candidate, Candidate...]
    # If we return a flat list of candidates, we need to attach "Origin" info to them?
    # SmartRollView (line 382) uses {roll.strike} {roll.type}
    # Those are properties of the CANDIDATE.
    
    flattened_rolls = []
    for s in suggestions:
        candidates = s.get("rolls", [])
        for c in candidates:
            # Attach origin context if needed?
            # c["origin_strike"] = ... 
            flattened_rolls.append(c)
            
    # Sort by score across all positions?
    flattened_rolls.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return flattened_rolls


@router.get("/api/news/{symbol}")
@log_endpoint
def get_ticker_news(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 5
):
    """
    Get aggregated news with sentiment and logic analysis for a ticker.
    """
    from app.services.news_sentiment import NewsSentimentService
    service = NewsSentimentService()
    return service.get_ticker_news(symbol, limit)

# --- X-DIV & Calendar Endpoints ---

@router.get("/api/opportunities")
@log_endpoint
def get_opportunities(
    current_user: Annotated[User, Depends(get_current_active_user)],
    source: str = None,
    limit: int = 100
):
    """
    Get persisted opportunities from the database.
    """
    from app.services.opportunity_service import OpportunityService
    service = OpportunityService()
    return service.get_opportunities(source=source, limit=limit)

@router.get("/analysis/dividend-capture")
@log_endpoint
def scan_dividend_capture(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[any, Depends(get_db)],
    force_scan: bool = False
):
    logging.info(f"User {current_user.username} requested Dividend Capture Scan (force_scan={force_scan}).")
    try:
        if not force_scan:
            # Return persisted results
            from app.services.opportunity_service import OpportunityService
            service = OpportunityService()
            results = service.get_opportunities(source="DividendScanner", limit=200)
            
            # Dedupe: Keep latest per symbol
            # Assuming results are sorted by created_at desc (or natural insertion order desc)
            # We use a dict to keep the first occurrence (latest)
            unique_results = {}
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            for r in results:
                proposal = r.get("proposal", {})
                sym = proposal.get("symbol")
                ex_date = proposal.get("ex_date")
                
                # Filter out past ex-dividend dates
                if ex_date and ex_date < today_str:
                    continue
                    
                if sym and sym not in unique_results:
                     unique_results[sym] = proposal
            
            return list(unique_results.values())

        # 1. Get Tickers from Portfolio and Tracked Stocks
        # db is already connected via dependency
        
        symbols_set = set()
        
        # Get symbols from latest portfolio holdings
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        if latest:
            query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
            holdings = list(db.ibkr_holdings.find(query, {"symbol": 1}))
            symbols_set.update([h["symbol"] for h in holdings if h.get("symbol")])
            logging.info(f"Adding portfolio symbols. Current count: {len(symbols_set)}")
        else:
            logging.warning("No portfolio holdings found.")
            
        # Get all tracked tickers from stock_data
        try:
            tracked_tickers = db.stock_data.distinct("Ticker")
            if tracked_tickers:
                symbols_set.update(tracked_tickers)
                logging.info(f"Adding tracked symbols. Total distinct count: {len(symbols_set)}")
        except Exception as e:
            logging.warning(f"Could not fetch tracked tickers: {e}")
            
        symbols = list(symbols_set)
        
        if not symbols:
            return []
            
        from app.services.dividend_scanner import DividendScanner
        scanner = DividendScanner()
        results = scanner.scan_dividend_capture_opportunities(symbols)
        logging.info(f"Scan complete. Found {len(results)} opportunities.")
        return results
    except Exception as e:
        logging.error(f"Error in scan_dividend_capture: {e}", exc_info=True)
        # Raise generic 500
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/dividend-capture/{ticker}")
@log_endpoint
def get_dividend_capture_analysis(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get detailed Buy-Write analysis for a ticker.
    """
    try:
        from app.services.dividend_scanner import DividendScanner
        scanner = DividendScanner()
        strategies = scanner.analyze_capture_strategy(ticker)
        return strategies
    except Exception as e:
        logging.error(f"Error getting analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/dividends.ics")
@log_endpoint
def get_dividend_calendar():
    """
    Generate an ICS calendar file (or text fallback) with upcoming Corporate Events (Ex-Div, Earnings).
    Persists daily files to 'xdivs/' directory to avoid re-fetching.
    """
    import yfinance as yf
    from fastapi.responses import Response, FileResponse
    import os

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cache_dir = "xdivs"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        
    filename = f"corporate_events_{today_str}.ics"
    file_path = os.path.join(cache_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/calendar", filename="corporate_events.ics")

    # 2. Generate if missing
    from app.services.dividend_scanner import DividendScanner
    scanner = DividendScanner()
    try:
        generated_path = scanner.generate_corporate_events_calendar()
        return FileResponse(generated_path, media_type="text/calendar", filename="corporate_events.ics")
    except Exception as e:
        # Fallback empty response or error
        return Response(content=f"Error generating calendar: {str(e)}", status_code=500)

@router.get("/api/macro")
@log_endpoint
def get_macro_summary(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get key macro economic indicators.
    """
    from app.services.macro_service import MacroService
    service = MacroService()
    return service.get_macro_summary()


@router.get("/analysis/signals/{ticker}")
@log_endpoint
def get_ticker_signals(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get experimental Kalman Filter and Markov Chain signals for a ticker.
    (Requires daily data history).
    """
    
    # 1. Fetch Data (optimize: use database if available and fresh)
    # For now, quick fetch
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        service = SignalService()
        
        kalman = service.get_kalman_signal(data)
        markov = service.get_markov_probabilities(data)
        advice = service.get_roll_vs_hold_advice(ticker, {}, mock_price_data=data)
        
        return {
            "ticker": ticker,
            "kalman": kalman,
            "markov": markov,
            "advice": advice
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
    # Define key indicators to fetch
    indicators = [
        {"id": "FEDFUNDS", "title": "Fed Funds Rate"},
        {"id": "CPIAUCSL", "title": "CPI Inflation"},
        {"id": "UNRATE", "title": "Unemployment Rate"}
    ]
    
    results = []
    for ind in indicators:
        val = service.fetch_indicator(ind["id"], ind["title"])
        if val:
            results.append(val)
            
    return {
        "market_regime": service.get_market_condition(),
        "indicators": results
    }

@router.get("/ticker/{symbol}")
@log_endpoint
def get_ticker_analysis(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get detailed analytics for a single ticker.
    Includes: Current Price, Stats, and basic metadata.
    """
    symbol = symbol.upper().strip()
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Fetch from stock_data
    stock = db.stock_data.find_one({"Ticker": symbol}, {"_id": 0})
    if not stock:
        # transform default structure if not found
        return {"symbol": symbol, "found": False, "price": 0.0}
        
    return {"symbol": symbol, "found": True, "data": stock}

@router.get("/opportunity/{symbol}")
@log_endpoint
def get_opportunity_analysis(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get 'Juicy' opportunity analysis for a ticker.
    """
    symbol = symbol.upper().strip()
    # reuse scanner service logic or just return raw data meant for opportunity view
    from app.services.scanner_service import scan_juicy_candidates
    
    # We might want to see if THIS specific symbol is juicy.
    # For now, let's fetch the stock data and run a quick check?
    # Or just return the pre-calculated metrics from the daily scan if available?
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    stock = db.stock_data.find_one({"Ticker": symbol}, {"_id": 0})
    
    if not stock: # fallback
         return {"symbol": symbol, "juicy_score": 0, "message": "Ticker not found in database"}

    # Calculate simple score on the fly (reusing logic from scanner conceptually)
    # TODO: Import a dedicated scorer
    iv_rank = stock.get("IV Rank", 0)
    liquidity = stock.get("Liquidity Rating", 0)
    
    score = 0
    reasons = []
    if iv_rank > 50: 
        score += 20
        reasons.append("High IV Rank")
    if liquidity > 3:
        score += 10
        reasons.append("High Liquidity")
        
    # --- Risk Analysis Integration ---
    from app.services.risk_service import RiskService
    risks = RiskService.analyze_risk(stock)
    
    return {
        "symbol": symbol,
        "juicy_score": score,
        "reasons": reasons,
        "risks": risks,  # New Field
        "metrics": {
             "iv_rank": iv_rank,
             "liquidity": liquidity,
             "call_put_skew": stock.get("Call/Put Skew"),
             "rsi_14": stock.get("RSI_14"),
             "atr_14": stock.get("ATR_14"),
        }
    }

@router.get("/portfolio/optimizer/{symbol}")
@log_endpoint
def get_portfolio_optimizer(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get optimization suggestions for a ticker (e.g. Covered Call candidates).
    """
    symbol = symbol.upper().strip()
    
    # Reuse option_optimizer.py logic if possible
    # For V1, we return a stub or simple suggestions based on price
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    stock = db.stock_data.find_one({"Ticker": symbol}, {"_id": 0})
    
    if not stock:
        return []
        
    price = stock.get("Current Price", 0)
    
    # Simple heuristic suggestions
    suggestions = []
    
    # 1. Covered Call (selling OTM)
    if price > 0:
        strike_target = price * 1.05 # 5% OTM
        suggestions.append({
            "strategy": "Covered Call",
            "action": "SELL CALL",
            "strike_target": round(strike_target, 1),
            "reason": "Generate Income (5% OTM Target)"
        })
        
        # 2. Cash Secured Put (buying dip)
        strike_dip = price * 0.90 # 10% OTM
        suggestions.append({
            "strategy": "Cash Secured Put",
            "action": "SELL PUT",
            "strike_target": round(strike_dip, 1),
            "reason": "Acquire at discount (-10% Target)"
        })

    # --- Smart Roll Assistant Integration ---
    # Check if we hold options for this ticker to suggest rolls
    holdings = list(db.ibkr_holdings.find({"symbol": symbol}, {"_id": 0}))
    if holdings:
        from app.services.roll_service import RollService
        roll_service = RollService()
        
        for pos in holdings:
            # We only care about options for rolling (secType usually 'OPT')
            if pos.get("secType") == "OPT":
                # Extract details (assuming standard IBKR fields)
                # We need strike, exp, right. 
                # Our schema might vary, let's try to extract safely.
                try:
                    current_strike = float(pos.get("strike", 0))
                    exp_date = pos.get("expiry") # Format might be YYYYMMDD or YYYY-MM-DD
                    if exp_date and len(exp_date) == 8:
                        exp_date = f"{exp_date[:4]}-{exp_date[4:6]}-{exp_date[6:]}"
                    
                    right = pos.get("right") # 'C' or 'P'
                    position = float(pos.get("position", 0))
                    
                    if position != 0:
                        position_type = "call" if right == "C" else "put"
                        # Use RollService
                        rolls = roll_service.find_rolls(
                            symbol=symbol,
                            current_strike=current_strike,
                            current_exp_date=exp_date,
                            position_type=position_type
                        )
                        
                        if "rolls" in rolls:
                             # Add top 3 rolls as suggestions
                             for r in rolls["rolls"][:3]:
                                 suggestions.append({
                                     "strategy": f"Roll {position_type.title()}",
                                     "action": f"ROLL to {r['expiration']} {r['strike']} ({r['roll_type']})",
                                     "reason": f"Net Credit: ${r['net_credit']:.2f}. {r['roll_type']} roll."
                                 })
                except Exception as e:
                    # Log error but don't break generic suggestions
                    print(f"Error calculating rolls for {symbol}: {e}")
    
    return suggestions


@router.get("/portfolio/export/csv")
@log_endpoint
def export_portfolio_csv(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Authenticated download endpoint (keeps previous behaviour).
    """
    return _get_portfolio_csv_response(username=current_user.username, origin="auth")


@router.post("/portfolio/export/url")
@log_endpoint
def create_portfolio_export_url(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Create a short-lived, one-time download URL for the authenticated user."""
    from datetime import datetime, timedelta
    from jose import jwt
    import logging

    logger = logging.getLogger(__name__)
    try:
        ttl = 60  # seconds
        payload = {
            "sub": current_user.username,
            "purpose": "download_portfolio",
            "exp": datetime.utcnow() + timedelta(seconds=ttl)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        url = f"/api/portfolio/export/csv/download?dl_token={token}"
        logger.info(f"Routes.create_portfolio_export_url - user={current_user.username} issued token, expires_in={ttl}s")
        return {"url": url, "expires_in": ttl}
    except Exception as e:
        logger.exception("Routes.create_portfolio_export_url - failed to create token")
        from fastapi.responses import Response
        import traceback
        error_msg = f"Failed to create download URL:\n{str(e)}\n\n{traceback.format_exc()}"
        return Response(content=error_msg, status_code=500, media_type="text/plain")


@router.get("/portfolio/export/csv/download")
@log_endpoint
def download_portfolio_with_token(dl_token: str):
    """Download endpoint that accepts a short-lived dl_token in querystring (no auth dependency)."""
    from jose import jwt
    import logging
    from fastapi.responses import Response

    logger = logging.getLogger(__name__)
    try:
        claims = jwt.decode(dl_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if claims.get("purpose") != "download_portfolio":
            raise Exception("Invalid token purpose")
        username = claims.get("sub")
        logger.info(f"Routes.download_portfolio_with_token - valid token for user={username}")
        return _get_portfolio_csv_response(username=username, origin="token")
    except Exception as e:
        logger.warning(f"Routes.download_portfolio_with_token - invalid/expired token: {e}")
        return Response(content="Invalid or expired download token", status_code=401, media_type="text/plain")


def _get_portfolio_csv_response(username: str, origin: str):
    """Internal helper to generate the Response for CSV data as plain text."""
    from fastapi.responses import Response
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Routes._get_portfolio_csv_response - start username={username} origin={origin}")

        from app.services.export_service import generate_portfolio_csv_content

        csv_content = generate_portfolio_csv_content()

        # Return as plain text for the frontend to handle in a new window/tab
        return Response(content=csv_content, media_type="text/plain")

    except Exception as e:
        logger.exception(f"Routes._get_portfolio_csv_response - exception for username={username}: {e}")
        error_msg = f"Export Failed:\n{str(e)}\n\n{traceback.format_exc()}"
        return Response(content=error_msg, status_code=500, media_type="text/plain")


# --- Tracked Ticker Management ---

class TickerInput(BaseModel):
    ticker: str

@router.get("/stocks/tracked", response_model=List[str])
@log_endpoint
def get_tracked_tickers(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get the list of tickers currently being tracked."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    
    tracked_list = sorted(doc["tickers"]) if doc and "tickers" in doc else []
    
    # Lazy Sync: Auto-add portfolio holdings for privileged users
    if current_user.role in ["admin", "portfolio"]:
        try:
            from app.services.ticker_discovery import discover_and_track_tickers
            new_list = discover_and_track_tickers()
            
            if new_list:
                # Update return list immediately so UI sees them
                tracked_list = sorted(list(set(tracked_list).union(new_list)))
                
                # Trigger background fetch for new info
                background_tasks.add_task(
                    background_job_wrapper, 
                    f"auto_add_{len(new_list)}", 
                    lambda: run_stock_live_comparison(new_list)
                )
        except Exception as e:
            # Log but don't fail the request
            print(f"Error in lazy portfolio sync: {e}")

    if tracked_list:
        return tracked_list
    
    # Fallback to defaults from script if not in DB yet (will trigger migration on next run)
    from app.services.stock_live_comparison import StockLiveComparison
    return StockLiveComparison.get_default_tickers()

@router.post("/stocks/tracked")
@log_endpoint
def add_tracked_ticker(
    ticker_input: TickerInput,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Add a ticker to the tracking list and trigger an immediate fetch."""
    ticker = ticker_input.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Update List
    # Use $addToSet to avoid duplicates
    result = db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$addToSet": {"tickers": ticker}},
        upsert=True
    )
    
    # 2. Trigger Fetch for this specific ticker
    from app.jobs import create_job
    job = create_job()
    
    # We use the existing function but pass only this ticker to limit scope
    background_tasks.add_task(background_job_wrapper, job.id, lambda: run_stock_live_comparison([ticker]))
    
    return {"status": "success", "message": f"Added {ticker} to tracking list.", "job_id": job.id}

@router.delete("/stocks/tracked/{ticker}")
@log_endpoint
def remove_tracked_ticker(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Remove a ticker from the tracking list."""
    ticker = ticker.upper().strip()
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Remove from List
    db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$pull": {"tickers": ticker}}
    )
    
    # Optional: Delete the actual data record?
    # User might want to keep history, but for "Live Comparison" it might be confusing to see it if it's not "Tracked".
    # But the "Live View" comes from /stocks which dumps everything. 
    # Let's LEAVE the data for now. The user can just ignore it, or we can add a cleanup later.
    
    return {"status": "success", "message": f"Removed {ticker} from tracking list."}
