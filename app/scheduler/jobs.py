from apscheduler.schedulers.background import BackgroundScheduler

from services.portfolio_fixer import run_portfolio_fixer
from services.stock_live_comparison import run_stock_live_comparison

scheduler = BackgroundScheduler()


def schedule_jobs() -> None:
    """Configure recurring jobs and start the scheduler."""
    scheduler.add_job(run_portfolio_fixer, trigger="cron", hour=3, minute=0)
    scheduler.add_job(run_stock_live_comparison, trigger="interval", hours=1)
    scheduler.start()
