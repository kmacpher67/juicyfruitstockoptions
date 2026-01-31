from datetime import timedelta
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import MongoClient

from app.auth.dependencies import get_current_active_user
from app.auth.utils import create_access_token, verify_password, get_password_hash
from app.config import settings
from app.models import Token, User, StockRecord, IBKRConfig, IBKRStatus, NavReportType
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import fetch_and_store_nav_report

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Authenticate against MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    user = db.users.find_one({"username": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

# --- Secured Endpoints ---

@router.get("/stocks", response_model=List[StockRecord])
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
def get_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    job = get_job(job_id)
    if not job:
          raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/run/stock-live-comparison")
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
def get_schedule(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    from app.scheduler.jobs import get_schedule_config
    return get_schedule_config()

@router.post("/schedule")
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
        last_sync=last_sync
    )

@router.post("/integrations/ibkr")
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
        
    db.system_config.update_one(
        {"_id": "ibkr_config"},
        {"$set": update_data},
        upsert=True
    )
    return {"status": "success"}

@router.post("/integrations/ibkr/test")
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
def get_portfolio_stats(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get calculated NAV stats (Current, 30d, YTD, etc)."""
    # Helper to protect View
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    from app.services.portfolio_analysis import get_nav_history_stats
    return get_nav_history_stats()

@router.get("/nav/report/{report_type}")
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
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Check Freshness
    # Look for raw report with this type ingested "today" (UTC)
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # We query the raw collection for metadata
    # We need to scan all accounts or just check if *any* exists?
    # Assuming single user/portfolio for now, or just check global existence.
    recent_entry = db.ibkr_raw_flex_reports.find_one({
        "ibkr_report_type": report_type,
        "_ingested_at": {"$gte": today_start}
    })
    
    if not recent_entry:
        # Trigger Fetch
        background_tasks.add_task(fetch_and_store_nav_report, report_type)
        return {"status": "fetching", "message": f"Report {report_type} requested. Check back soon."}
        
    # 2. Return Data
    # What data to return?
    # The user likely wants the *parsed* history that helps the UI chart.
    # But since the request is generic, maybe we return the raw rows or the Nav Stats?
    # Let's return the simplified stats closest to the report type.
    # Actually, returning "available" allows the frontend to then call /portfolio/stats or similar
    # which aggregates everything.
    # BUT, if the user requested NAV7D, maybe they specifically want the 7-day series?
    # For now, let's return a success status and the timestamp.
    
    return {
        "status": "available", 
        "last_updated": recent_entry.get("_ingested_at"),
        "report_type": report_type
    }

@router.get("/portfolio/holdings")
def get_portfolio_holdings(
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
    return data

@router.get("/portfolio/alerts")
def get_portfolio_alerts(
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
