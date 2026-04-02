from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

from pymongo import MongoClient

from app.config import settings
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import run_ibkr_sync
from app.services.ibkr_tws_service import get_ibkr_tws_service
from app.services.dividend_scanner import DividendScanner
from app.services.expiration_scanner import ExpirationScanner
import logging
import json
import os

scheduler = BackgroundScheduler()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client.get_default_database("stock_analysis")


def _get_tws_accounts(tws_service) -> list[str]:
    accounts: set[str] = set()
    app = tws_service.app
    if app is None:
        return []

    for position in tws_service.get_positions():
        account = position.get("account") or position.get("account_id")
        if account:
            accounts.add(account)

    for account_name, _ in app.account_values.keys():
        if account_name:
            accounts.add(account_name)

    return sorted(accounts)


def _log_tws_skip(job_name: str, cause: str, live_status: dict | None = None) -> None:
    live_status = live_status or {}
    logging.warning(
        "Scheduler: Skipping %s cause=%s state=%s socket_connectable=%s handshake_attempted=%s "
        "managed_accounts=%s position_count=%s last_account_value_update=%s last_error=%s",
        job_name,
        cause,
        live_status.get("connection_state"),
        live_status.get("socket_connectable"),
        live_status.get("handshake_attempted"),
        live_status.get("managed_accounts"),
        live_status.get("position_count"),
        live_status.get("last_account_value_update"),
        live_status.get("last_error"),
    )


def run_tws_position_sync():
    """Persist the latest TWS positions into ibkr_holdings as a live snapshot."""
    if not settings.IBKR_TWS_ENABLED:
        _log_tws_skip("TWS position sync", "disabled_flag")
        return

    tws_service = get_ibkr_tws_service()
    if not tws_service.ensure_connected():
        live_status = tws_service.get_live_status()
        cause = {
            "disabled": "disabled_flag",
            "handshake_failed": "no_handshake",
            "socket_unreachable": "socket_unreachable",
            "disconnected": "disconnected",
        }.get(live_status.get("connection_state"), "not_connected")
        _log_tws_skip("TWS position sync", cause, live_status)
        return

    positions = tws_service.get_positions()
    if not positions:
        live_status = tws_service.get_live_status()
        cause = "no_positions"
        if not live_status.get("managed_accounts"):
            cause = "no_managed_accounts"
        _log_tws_skip("TWS position sync", cause, live_status)
        return

    db = _get_db()
    now = _utc_now()
    snapshot_id = f"tws_{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    report_date = now.strftime("%Y-%m-%d")
    synced_count = 0

    for position in positions:
        account_id = position.get("account") or position.get("account_id")
        symbol = position.get("symbol")
        sec_type = position.get("sec_type") or position.get("secType") or "UNKNOWN"
        position_key = position.get("position_key")
        if not account_id or not symbol:
            continue
        if not position_key:
            local_symbol = position.get("local_symbol") or symbol
            position_key = f"{account_id}:{sec_type}:{local_symbol}"

        doc = dict(position)
        doc.update(
            {
                "account_id": account_id,
                "date": now,
                "report_date": report_date,
                "snapshot_id": snapshot_id,
                "position_key": position_key,
                "quantity": position.get("position", 0),
                "secType": sec_type,
                "source": "tws",
                "last_tws_update": now,
            }
        )

        db.ibkr_holdings.update_one(
            {
                "snapshot_id": snapshot_id,
                "position_key": position_key,
                "account_id": account_id,
                "source": "tws",
            },
            {"$set": doc},
            upsert=True,
        )
        synced_count += 1

    logging.info(
        "Scheduler: TWS position sync stored %s positions in snapshot %s.",
        synced_count,
        snapshot_id,
    )


def run_tws_nav_snapshot():
    """Append live account NAV snapshots from TWS into ibkr_nav_history."""
    if not settings.IBKR_TWS_ENABLED:
        _log_tws_skip("TWS NAV snapshot", "disabled_flag")
        return

    tws_service = get_ibkr_tws_service()
    if not tws_service.ensure_connected():
        live_status = tws_service.get_live_status()
        cause = {
            "disabled": "disabled_flag",
            "handshake_failed": "no_handshake",
            "socket_unreachable": "socket_unreachable",
            "disconnected": "disconnected",
        }.get(live_status.get("connection_state"), "not_connected")
        _log_tws_skip("TWS NAV snapshot", cause, live_status)
        return

    accounts = _get_tws_accounts(tws_service)
    if not accounts:
        live_status = tws_service.get_live_status()
        _log_tws_skip("TWS NAV snapshot", "no_managed_accounts", live_status)
        return

    db = _get_db()
    now = _utc_now()
    report_date = now.strftime("%Y-%m-%d")
    inserted = 0

    for account in accounts:
        values = tws_service.get_account_values(account)
        if not values:
            logging.warning(
                "Scheduler: Skipping TWS NAV snapshot for account=%s cause=no_account_values",
                account,
            )
            continue

        def _float_value(key: str) -> float:
            payload = values.get(key) or {}
            try:
                return float(payload.get("value") or 0)
            except (TypeError, ValueError):
                return 0.0

        nav = _float_value("NetLiquidation")
        doc = {
            "account_id": account,
            "_report_date": report_date,
            "timestamp": now,
            "source": "tws",
            "ending_value": nav,
            "total_nav": nav,
            "unrealized_pnl": _float_value("UnrealizedPnL"),
            "realized_pnl": _float_value("RealizedPnL"),
            "last_tws_update": now,
        }
        db.ibkr_nav_history.insert_one(doc)
        inserted += 1

    logging.info("Scheduler: TWS NAV snapshot stored %s account snapshots.", inserted)


def run_tws_execution_sync():
    """Persist current-day TWS executions into ibkr_trades."""
    if not settings.IBKR_TWS_ENABLED:
        _log_tws_skip("TWS execution sync", "disabled_flag")
        return

    tws_service = get_ibkr_tws_service()
    if not tws_service.ensure_connected():
        live_status = tws_service.get_live_status()
        cause = {
            "disabled": "disabled_flag",
            "handshake_failed": "no_handshake",
            "socket_unreachable": "socket_unreachable",
            "disconnected": "disconnected",
        }.get(live_status.get("connection_state"), "not_connected")
        _log_tws_skip("TWS execution sync", cause, live_status)
        return

    accounts = _get_tws_accounts(tws_service)
    requested = False
    if accounts:
        for index, account in enumerate(accounts):
            requested = tws_service.refresh_executions(account=account, req_id=9100 + index) or requested
    else:
        requested = tws_service.refresh_executions() or requested

    if not requested:
        live_status = tws_service.get_live_status()
        _log_tws_skip("TWS execution sync", "request_not_issued", live_status)
        return

    db = _get_db()
    upserted = tws_service.upsert_executions_to_db(db=db)
    live_status = tws_service.get_live_status()
    logging.info(
        "Scheduler: TWS execution sync upserted %s live execution(s). "
        "execution_count=%s last_execution_update=%s",
        upserted,
        live_status.get("execution_count"),
        live_status.get("last_execution_update"),
    )


def run_tws_order_sync():
    """Persist active TWS open orders into ibkr_orders."""
    if not settings.IBKR_TWS_ENABLED:
        _log_tws_skip("TWS order sync", "disabled_flag")
        return

    tws_service = get_ibkr_tws_service()
    if not tws_service.ensure_connected():
        live_status = tws_service.get_live_status()
        cause = {
            "disabled": "disabled_flag",
            "handshake_failed": "no_handshake",
            "socket_unreachable": "socket_unreachable",
            "disconnected": "disconnected",
        }.get(live_status.get("connection_state"), "not_connected")
        _log_tws_skip("TWS order sync", cause, live_status)
        return

    if not tws_service.refresh_open_orders():
        live_status = tws_service.get_live_status()
        _log_tws_skip("TWS order sync", "request_not_issued", live_status)
        return

    db = _get_db()
    upserted = tws_service.upsert_open_orders_to_db(db=db)
    live_status = tws_service.get_live_status()
    logging.info(
        "Scheduler: TWS order sync upserted %s open order(s). "
        "order_count=%s last_order_update=%s",
        upserted,
        live_status.get("order_count"),
        live_status.get("last_order_update"),
    )


def tag_existing_flex_sync_sources():
    """Additive metadata tag so downstream consumers can distinguish Flex from TWS."""
    db = _get_db()
    holdings_result = db.ibkr_holdings.update_many(
        {"source": {"$exists": False}},
        {"$set": {"source": "flex"}},
    )
    nav_result = db.ibkr_nav_history.update_many(
        {"source": {"$exists": False}},
        {"$set": {"source": "flex"}},
    )
    logging.info(
        "Scheduler: Tagged Flex source metadata on %s holdings docs and %s NAV docs.",
        holdings_result.modified_count,
        nav_result.modified_count,
    )

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
    tag_existing_flex_sync_sources()
    
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

    scheduler.add_job(
        run_tws_position_sync,
        trigger="interval",
        seconds=30,
        id="tws_position_sync",
        replace_existing=True
    )
    logging.info("Scheduled TWS Position Sync every 30 seconds.")

    scheduler.add_job(
        run_tws_nav_snapshot,
        trigger="interval",
        minutes=3,
        id="tws_nav_snapshot",
        replace_existing=True
    )
    logging.info("Scheduled TWS NAV Snapshot every 3 minutes.")

    scheduler.add_job(
        run_tws_execution_sync,
        trigger="interval",
        seconds=30,
        id="tws_execution_sync",
        replace_existing=True
    )
    logging.info("Scheduled TWS Execution Sync every 30 seconds.")

    scheduler.add_job(
        run_tws_order_sync,
        trigger="interval",
        seconds=30,
        id="tws_order_sync",
        replace_existing=True
    )
    logging.info("Scheduled TWS Order Sync every 30 seconds.")

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
             scanner.generate_corporate_events_calendar()
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

    # --- Recommendation Database Scans ---
    def run_recommendation_scans():
        """Run daily scans and persist validation."""
        import logging
        from app.services.scanner_service import scan_momentum_calls, scan_juicy_candidates
        from app.services.roll_service import RollService
        from app.services.signal_service import SignalService
        from pymongo import MongoClient
        
        logging.info("Scheduler: Starting Recommendation Scans (Persistence Enabled)")
        
        # 1. Scanners (Market Wide)
        try:
             scan_momentum_calls(persist=True)
             scan_juicy_candidates(persist=True)
             logging.info("Scheduler: Scanners completed.")
        except Exception as e:
             logging.error(f"Scheduler: Scanner failed: {e}")

        # 2. Portfolio Rolls & Signals (Holdings)
        try:
             client = MongoClient(settings.MONGO_URI)
             db = client.get_default_database("stock_analysis")
             
             # Get Tickers
             latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
             if latest:
                 query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
                 holdings = list(db.ibkr_holdings.find(query))
                 # Filter valid tickers
                 tickers = []
                 for h in holdings:
                     sym = h.get("underlying_symbol") or h.get("symbol")
                     if sym: tickers.append(sym)
                 tickers = list(set(tickers))
                 
                 # Roll Service
                 roll_service = RollService()
                 roll_service.analyze_portfolio_rolls(holdings, persist=True)
                 logging.info("Scheduler: Portfolio Rolls analysis completed.")
                 
                 # Signal Service
                 signal_service = SignalService()
                 signal_service.scan_and_persist_signals(tickers)
                 logging.info("Scheduler: Signal Scan completed.")
                 
        except Exception as e:
             logging.error(f"Scheduler: Portfolio/Signal scan failed: {e}")
             
        logging.info("Scheduler: Recommendation Scans Finished.")

    # Schedule: 10:15 AM (Morning)
    scheduler.add_job(
        run_recommendation_scans,
        trigger="cron", 
        day_of_week='mon-fri',
        hour=10, 
        minute=15,
        id="recommendation_scans_morning",
        replace_existing=True
    )
    
    # Schedule: 4:30 PM (Post-Market)
    scheduler.add_job(
        run_recommendation_scans,
        trigger="cron", 
        day_of_week='mon-fri',
        hour=16, 
        minute=30,
        id="recommendation_scans_afternoon",
        replace_existing=True
    )
    logging.info("Scheduled Recommendation Scans (10:15, 16:30).")

    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
