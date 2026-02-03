from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import run_ibkr_sync
from app.services.dividend_scanner import DividendScanner
from app.services.expiration_scanner import ExpirationScanner
import logging
import json
import os

scheduler = BackgroundScheduler()

def get_schedule_config():
    """Load schedule from MongoDB or default to 10:00."""
    try:
        from pymongo import MongoClient
        # Use settings.MONGO_URI from config
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        config = db.system_config.find_one({"_id": "daily_schedule"})
        
        if config:
            return {"hour": config.get("hour"), "minute": config.get("minute")}
    except Exception as e:
        logging.error(f"Failed to load schedule from Mongo: {e}")
    
    # Default Fallback (10:00 AM)
    return {"hour": 10, "minute": 0}

def save_schedule_config(hour, minute):
    """Persist schedule to MongoDB."""
    try:
        from pymongo import MongoClient
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        db.system_config.update_one(
            {"_id": "daily_schedule"},
            {"$set": {"hour": hour, "minute": minute}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Failed to save schedule config: {e}")

def reschedule_daily_job(hour: int, minute: int):
    """Update the running job and save config."""
    # Reschedule Verification
    try:
        scheduler.reschedule_job(
            "stock_comparison_job",
            trigger="cron",
            hour=hour,
            minute=minute
        )
    except Exception as e:
         logging.warning(f"Failed to reschedule stock_comparison_job: {e}")

    # Reschedule IBKR Sync
    try:
        scheduler.reschedule_job(
            "ibkr_sync_job",
            trigger="cron",
            hour=hour,
            minute=minute
        )
    except Exception as e:
         logging.warning(f"Failed to reschedule ibkr_sync_job: {e}")

    save_schedule_config(hour, minute)
    logging.info(f"Rescheduled Daily Jobs to {hour:02d}:{minute:02d}")

def start_scheduler():
    """Configure and start the background scheduler."""
    logging.info("Starting Scheduler...")
    
    # Load Config
    config = get_schedule_config()
    hour = config.get("hour", 10)
    minute = config.get("minute", 0)
    
    # Stock Live Comparison Job
    scheduler.add_job(
        run_stock_live_comparison, 
        trigger="cron", 
        hour=hour, 
        minute=minute,
        id="stock_comparison_job",
        replace_existing=True
    )
    logging.info(f"Scheduled Stock Comparison for {hour:02d}:{minute:02d} daily.")

    # IBKR Sync Job
    scheduler.add_job(
        run_ibkr_sync, 
        trigger="cron", 
        hour=hour, 
        minute=minute,
        id="ibkr_sync_job",
        replace_existing=True
    )
    logging.info(f"Scheduled IBKR Sync for {hour:02d}:{minute:02d} daily.")

    # Portfolio Fixer (Keep existing 3am logic)
    scheduler.add_job(
        run_portfolio_fixer, 
        trigger="cron", 
        hour=3, 
        minute=0,
        id="portfolio_fixer_job",
        replace_existing=True
    )
    logging.info("Scheduled Portfolio Fixer for 03:00 daily.")

    # --- Dividend Scanner Jobs ---
    def run_dividend_scan_wrapper():
        """Wrapper to instantiate scanner and run."""
        from app.services.dividend_scanner import DividendScanner
        from pymongo import MongoClient
        
        # 1. Fetch Tickers
        try:
             client = MongoClient(settings.MONGO_URI)
             db = client.get_default_database("stock_analysis")
             latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
             if latest:
                 query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
                 holdings = list(db.ibkr_holdings.find(query, {"symbol": 1}))
                 tickers = list(set([h["symbol"] for h in holdings]))
                 
                 if tickers:
                     logging.info(f"Scheduler: Starting Dividend Scan for {len(tickers)} tickers.")
                     scanner = DividendScanner()
                     scanner.scan_dividend_capture_opportunities(tickers)
                     logging.info("Scheduler: Dividend Scan Completed.")
        except Exception as e:
            logging.error(f"Scheduler: Failed to run dividend scan: {e}")

    # 1. Market Hours (Monday-Friday, 9:30 - 16:00, every 30 mins)
    # Cron: Mon-Fri, 9-16 hour, 0,30 minute
    scheduler.add_job(
        run_dividend_scan_wrapper,
        trigger="cron",
        day_of_week='mon-fri',
        hour='9-16',
        minute='0,30',
        id='dividend_market_hours',
        replace_existing=True
    )
    
    # 2. Pre-Market (8:30 AM)
    scheduler.add_job(
        run_dividend_scan_wrapper,
        trigger="cron",
        day_of_week='mon-fri',
        hour='8',
        minute='30',
        id='dividend_pre_market',
        replace_existing=True
    )
    
    # 3. Post-Market (5:00 PM)
    scheduler.add_job(
        run_dividend_scan_wrapper,
        trigger="cron",
        day_of_week='mon-fri',
        hour='17',
        minute='0',
        id='dividend_post_market',
        replace_existing=True
    )
    logging.info("Scheduled Dividend Scans (Pre/Market/Post).")
    # --- Dividend Calendar Generation Job ---
    def run_dividend_calendar_job():
        """Wrapper for ICS generation."""
        try:
             from app.services.dividend_scanner import DividendScanner
             logging.info("Scheduler: Starting Dividend Calendar Generation.")
             scanner = DividendScanner()
             scanner.generate_dividend_calendar()
             logging.info("Scheduler: Dividend Calendar Generation Completed.")
        except Exception as e:
            logging.error(f"Scheduler: Failed to generate dividend calendar: {e}")

    # Run daily at 6:00 AM
    scheduler.add_job(
        run_dividend_calendar_job,
        trigger="cron",
        day_of_week='mon-sun',
        hour='6',
        minute='0',
        id='dividend_calendar_gen',
        replace_existing=True
    )
    logging.info("Scheduled Dividend Calendar Generation (Daily 06:00).")

    # --- Expiration Scanner Job ---
    def run_expiration_scan_wrapper():
        """Wrapper to run Expiration Scanner."""
        try:
             logging.info("Scheduler: Starting Expiration Scan.")
             scanner = ExpirationScanner()
             scanner.scan_portfolio_expirations(days_threshold=7)
             logging.info("Scheduler: Expiration Scan Completed.")
        except Exception as e:
            logging.error(f"Scheduler: Failed to run expiration scan: {e}")

    # Daily at 9:30 AM (Market Open)
    scheduler.add_job(
        run_expiration_scan_wrapper,
        trigger="cron",
        day_of_week='mon-fri',
        hour='9',
        minute='30',
        id='expiration_scanner_daily',
        replace_existing=True
    )
    logging.info("Scheduled Expiration Scanner (Daily 09:30).")

    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
