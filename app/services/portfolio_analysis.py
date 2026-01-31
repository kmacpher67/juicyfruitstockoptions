from datetime import datetime, timedelta
import logging
from pymongo import MongoClient
from app.config import settings

def get_nav_history_stats():
    """
    Calculate NAV Stats using authoritative 'ibkr_nav_history' collection.
    Uses specific IBKR Report Types (1D, 7D, 30D, etc) for precise calculations.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    from app.models import NavReportType

    stats = {
        "current_nav": 0,
        "change_1d": None, "change_7d": None, "change_30d": None,
        "change_mtd": None, "change_ytd": None, "change_yoy": None, # 1Y
        "start_1d": None, "start_7d": None, "start_30d": None,
        "start_mtd": None, "start_ytd": None, "start_yoy": None,
        "history": []
    }
    
    # helper to aggregate across accounts for the latest available date
    def get_aggregated_stats(rtype: NavReportType):
        # 1. Find the most recent date for this specific report type
        # We sort by _report_date descending to get the "latest batch"
        latest_entry = db.ibkr_nav_history.find_one(
            {"ibkr_report_type": rtype.value},
            sort=[("_report_date", -1)]
        )
        if not latest_entry:
            return None
            
        target_date = latest_entry["_report_date"]
        
        # 2. Sum up all accounts for that specific date
        pipeline = [
            {"$match": {
                "ibkr_report_type": rtype.value, 
                "_report_date": target_date
            }},
            {"$group": {
                "_id": None,
                "total_start": {"$sum": "$starting_value"},
                "total_end": {"$sum": "$ending_value"},
                # We cannot average TWRs. We calculate the portfolio return from the summed totals.
            }}
        ]
        
        results = list(db.ibkr_nav_history.aggregate(pipeline))
        if not results:
            return None
            
        return results[0] # {total_start: X, total_end: Y}

    # 1. Fetch Aggregated Stats
    s_1d = get_aggregated_stats(NavReportType.NAV_1D)
    s_7d = get_aggregated_stats(NavReportType.NAV_7D)
    s_30d = get_aggregated_stats(NavReportType.NAV_30D)
    s_mtd = get_aggregated_stats(NavReportType.NAV_MTD)
    s_ytd = get_aggregated_stats(NavReportType.NAV_YTD)
    s_1y = get_aggregated_stats(NavReportType.NAV_1Y)
    
    # 2. Extract Data
    # Current NAV comes from the sum of Ending Values of the 1D report (Total Assets)
    if s_1d:
        stats["current_nav"] = s_1d.get("total_end", 0)
        
    def extract_stats(agg_res, suffix):
        if not agg_res: return
        start = agg_res.get("total_start", 0)
        end = agg_res.get("total_end", 0)
        
        # Populate Start (for Tooltips)
        stats[f"start_{suffix}"] = start
        
        # Calculate % Change from the Totals
        # ((TotalEnd - TotalStart) / TotalStart) * 100
        if start and start != 0:
             stats[f"change_{suffix}"] = ((end - start) / start) * 100
        else:
             stats[f"change_{suffix}"] = 0.0
             
    extract_stats(s_1d, "1d")
    extract_stats(s_7d, "7d")
    extract_stats(s_30d, "30d")
    extract_stats(s_mtd, "mtd")
    extract_stats(s_ytd, "ytd")
    extract_stats(s_1y, "yoy")

    # 3. History Graph
    # For the graph, we need a time seriesSum of all accounts per day.
    # We use the NAV_1D report type as the authoritative daily snapshot.
    pipeline = [
        {"$match": {"ibkr_report_type": NavReportType.NAV_1D.value}},
        {
            "$group": {
                "_id": "$_report_date", # Group by Date
                "total_nav": {"$sum": "$ending_value"}
            }
        },
        {"$sort": {"_id": 1}}, # Chronological
        {"$project": {
            "date": "$_id",
            "nav": "$total_nav",
            "_id": 0
        }}
    ]
    history_docs = list(db.ibkr_nav_history.aggregate(pipeline))
    
    # Fallback: if new history is empty (transition period), use old schema query?
    # The old schema used "report_date" and "total_nav".
    if not history_docs:
         pipeline_legacy = [
            {"$match": {"ibkr_report_type": {"$exists": False}}}, # Old records
            {
                "$group": {
                    "_id": "$report_date",
                    "total_nav": {"$sum": "$total_nav"}
                }
            },
            {"$sort": {"_id": 1}},
            {"$project": {"date": "$_id", "nav": "$total_nav", "_id": 0}}
        ]
         history_docs = list(db.ibkr_nav_history.aggregate(pipeline_legacy))
         
    stats["history"] = history_docs
    
    return stats

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
