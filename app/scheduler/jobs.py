from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
import logging

scheduler = BackgroundScheduler()

def start_scheduler():
    """Configure and start the background scheduler."""
    logging.info("Starting Scheduler...")
    
    # Parse RUN_TIME (e.g. "16:00")
    try:
        hour, minute = map(int, settings.RUN_TIME.split(":"))
    except ValueError:
        hour, minute = 16, 0 # Default fallback
    
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
