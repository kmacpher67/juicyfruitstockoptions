from datetime import datetime, timedelta
import logging
from pymongo import MongoClient
from app.config import settings

def get_nav_history_stats():
    """
    Calculate NAV Stats using authoritative 'ibkr_nav_history' collection.
    Aggregates all accounts (Taxable + IRA) for a Total Portfolio View.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Aggregate Total NAV per Date (Summing across all accounts)
    pipeline = [
        {
            "$group": {
                "_id": "$report_date", # Group by Date (YYYY-MM-DD)
                "total_nav": {"$sum": "$total_nav"},
                "accounts": {"$addToSet": "$account_id"}
            }
        },
        {"$sort": {"_id": 1}} # Chronological
    ]
    
    # List of { _id: "2025-01-01", total_nav: 12345.67 }
    history = list(db.ibkr_nav_history.aggregate(pipeline))
    
    if not history:
        return {
            "current_nav": 0,
            "change_1d": 0, "change_30d": 0, "change_mtd": 0, "change_ytd": 0, "change_yoy": 0,
            "history": []
        }
    
    # Helper to find NAV for a specific date (or closest previous)
    # Since list is sorted, we can bisect or iterate. Given size (years), simple iter is fine.
    
    date_map = {d["_id"]: d["total_nav"] for d in history}
    sorted_dates = sorted(date_map.keys())
    
    def get_nav_at(target_date_str):
        # Find exact or closest previous date
        # target_date_str: YYYY-MM-DD
        closest_date = None
        for d in sorted_dates:
            if d <= target_date_str:
                closest_date = d
            else:
                break
        return date_map.get(closest_date) if closest_date else None

    # Current
    current_date = sorted_dates[-1]
    current_nav = date_map[current_date]
    
    # Target Dates
    now = datetime.strptime(current_date, "%Y-%m-%d") # Use data's last date as 'now' anchor? 
    # Actually, for YTD, we want Jan 1 of the CURRENT year relative to real time, or data time?
    # Let's use Real Time for "YTD" (Year To Date), allowing for stale data if import missed.
    # BUT if data ends in 2025 and it's 2026, YTD is 0. 
    # Let's align "Now" to the latest data point for reporting (avoiding zeros if data is old).
    
    anchor_date = now # The date of the last data point
    year_start = datetime(anchor_date.year, 1, 1).strftime("%Y-%m-%d")
    month_start = datetime(anchor_date.year, anchor_date.month, 1).strftime("%Y-%m-%d")
    
    day_1_ago = (anchor_date - timedelta(days=1)).strftime("%Y-%m-%d")
    day_30_ago = (anchor_date - timedelta(days=30)).strftime("%Y-%m-%d")
    year_ago = (anchor_date - timedelta(days=365)).strftime("%Y-%m-%d")
    
    nav_1d = get_nav_at(day_1_ago) or current_nav
    nav_30d = get_nav_at(day_30_ago) or current_nav
    nav_mtd = get_nav_at(month_start) or current_nav
    nav_ytd = get_nav_at(year_start) or current_nav
    nav_yoy = get_nav_at(year_ago) or current_nav
    
    def pct(start, end):
        if not start or start == 0: return 0.0
        return ((end - start) / start) * 100

    return {
        "current_nav": current_nav,
        "change_1d": pct(nav_1d, current_nav),
        "change_30d": pct(nav_30d, current_nav),
        "change_mtd": pct(nav_mtd, current_nav),
        "change_ytd": pct(nav_ytd, current_nav),
        "change_yoy": pct(nav_yoy, current_nav),
        "history": [{"date": d["_id"], "nav": d["total_nav"]} for d in history]
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
