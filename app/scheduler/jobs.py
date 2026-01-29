from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import run_ibkr_sync
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
    
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
