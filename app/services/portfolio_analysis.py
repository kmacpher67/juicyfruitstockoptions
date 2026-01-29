from datetime import datetime, timedelta
import logging
from pymongo import MongoClient
from app.config import settings

def get_nav_history_stats():
    """
    Calculate NAV Stats: Current, 30d %, MTD %, YTD %, YoY %.
    Returns: Dict with stats and history graph data.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Get Daily Total NAVs
    # Aggregate by report_date
    # 1. Get NAV History (Aggregated by Snapshot)
    # Group by 'snapshot_id' first to get valid totals for that point in time
    pipeline = [
        {
            "$group": {
                "_id": "$snapshot_id", # Group by the unique sync batch
                "total_nav": {"$sum": "$market_value"},
                "date": {"$first": "$date"},
                "report_date": {"$first": "$report_date"}
            }
        },
        {"$sort": {"date": 1}} # Sort chronological
    ]
    
    # Each document in 'snapshots' is now a valid Full Portfolio NAV at that time
    snapshots = list(db.ibkr_holdings.aggregate(pipeline))
    
    if not snapshots:
        return {
            "current_nav": 0,
            "change_1d": 0, "change_30d": 0, "change_mtd": 0, "change_ytd": 0, "change_yoy": 0,
            "history": []
        }
    
    # Logic: To create a Daily History (1 point per day), we pick the LAST snapshot of each day.
    # But for 'history' graph, showing intraday might be noisy? Let's stick to Daily for the stats keys.
    
    history_map = {} # Key: YYYY-MM-DD
    for s in snapshots:
        d_str = s["date"].strftime("%Y-%m-%d") # Use ingestion time
        history_map[d_str] = s # Overwrites, so ends up with the last one of the day
        
    # Convert map back to sorted list
    daily_history = sorted(history_map.values(), key=lambda x: x["date"])
    
    # History for Graph (Daily)
    history = [{"date": d["date"].strftime("%Y-%m-%d"), "nav": d["total_nav"]} for d in daily_history]
    
    # Current is simply the very last snapshot (could be intraday)
    current_snapshot = snapshots[-1]
    current = history[-1]
    
    def get_pct_change(start_nav, end_nav):
        if start_nav == 0: return 0.0
        return ((end_nav - start_nav) / start_nav) * 100

    def find_nav_closest_to(target_date_str):
        # target_date_str: "YYYY-MM-DD"
        # Find entry <= target_date
        # Simple search since list is sorted
        candidate = None
        for entry in history:
            if entry["date"] <= target_date_str:
                candidate = entry
            else:
                break
        return candidate.get("nav") if candidate else None

    now = datetime.utcnow()
    year_start = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
    month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
    day_30_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    year_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    current_nav = current["nav"]
    
    # Calculate Changes
    nav_1d = find_nav_closest_to(yesterday) or current_nav
    nav_30d = find_nav_closest_to(day_30_ago) or current_nav
    nav_mtd = find_nav_closest_to(month_start) or current_nav # If data starts mid-month, uses first available
    nav_ytd = find_nav_closest_to(year_start) or current_nav
    nav_yoy = find_nav_closest_to(year_ago) or current_nav

    return {
        "current_nav": current_nav,
        "change_1d": get_pct_change(nav_1d, current_nav),
        "change_30d": get_pct_change(nav_30d, current_nav),
        "change_mtd": get_pct_change(nav_mtd, current_nav),
        "change_ytd": get_pct_change(nav_ytd, current_nav),
        "change_yoy": get_pct_change(nav_yoy, current_nav),
        "history": history[-90:] # Return last 90 days for sparkline?
    }

def run_portfolio_analysis():
    """
    Generate AI Insights based on latest portfolio data.
    1. Drift Detection (Concentration Risk)
    2. Tax Harvesting Opportunities
    3. Execution Quality (Slippage)
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Fetch Latest Holdings Snapshot
    # Since we are time-series, we need the latest 'report_date'
    latest_holding = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest_holding:
        logging.info("Analysis Skipped: No holdings data.")
        return
        
    report_date = latest_holding.get("report_date")
    # Fetch all for this date
    holdings = list(db.ibkr_holdings.find({"report_date": report_date}))
    
    insights = []
    
    # --- Drift Detection ---
    NAV_THRESHOLD = 0.05 # 5%
    for h in holdings:
        pct = h.get("percent_of_nav", 0)
        sym = h.get("symbol")
        if pct > NAV_THRESHOLD and sym != "USD": # Ignore Cash
            insights.append({
                "type": "DRIFT",
                "severity": "HIGH",
                "symbol": sym,
                "message": f"Concentration Risk: {sym} constitutes {pct*100:.1f}% of NAV (Limit: {NAV_THRESHOLD*100}%)."
            })

    # --- Tax Harvesting ---
    LOSS_THRESHOLD = -1000
    for h in holdings:
        pnl = h.get("unrealized_pnl", 0)
        sym = h.get("symbol")
        if pnl < LOSS_THRESHOLD:
             insights.append({
                "type": "TAX",
                "severity": "MEDIUM",
                "symbol": sym,
                "message": f"Tax Harvesting Opportunity: {sym} has unrealized loss of ${pnl:,.2f}."
            })
            
    # --- Store Insights ---
    # We replace old insights or keep history? Let's keep history but mark 'active'.
    # For now, just a simple log of 'active' insights.
    if insights:
        db.portfolio_insights.insert_many([
            {**i, "created_at": latest_holding.get("date"), "report_date": report_date} 
            for i in insights
        ])
        logging.info(f"Generated {len(insights)} AI insights.")
    else:
        logging.info("No new insights generated.")

if __name__ == "__main__":
    run_portfolio_analysis()
