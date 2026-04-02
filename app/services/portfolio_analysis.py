from datetime import datetime, timedelta, timezone
import logging
from pymongo import MongoClient
from app.config import settings
from app.models import NavReportType


def _normalize_account_id(account_id: str | None) -> str | None:
    if account_id is None:
        return None
    normalized = str(account_id).strip()
    if not normalized:
        return None
    if normalized.upper() == "ALL":
        return None
    return normalized


def _coerce_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _is_recent_live_timestamp(value, max_age_minutes: int = 5) -> bool:
    parsed = _coerce_datetime(value)
    if not parsed:
        return False
    now = datetime.now(timezone.utc)
    return (now - parsed) <= timedelta(minutes=max_age_minutes)


def get_latest_live_nav_snapshot(account_id: str | None = None):
    """Return the latest intraday TWS NAV snapshot if available."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    normalized_account = _normalize_account_id(account_id)
    match_filter = {"source": "tws"}
    if normalized_account:
        match_filter["account_id"] = normalized_account

    pipeline = [
        {"$match": match_filter},
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$timestamp",
                "total_nav": {"$sum": {"$ifNull": ["$total_nav", "$ending_value"]}},
                "unrealized_pnl": {"$sum": {"$ifNull": ["$unrealized_pnl", 0]}},
                "realized_pnl": {"$sum": {"$ifNull": ["$realized_pnl", 0]}},
                "accounts": {"$addToSet": "$account_id"},
                "last_tws_update": {"$max": "$last_tws_update"},
            }
        },
        {"$sort": {"_id": -1}},
        {"$limit": 1},
    ]

    results = list(db.ibkr_nav_history.aggregate(pipeline))
    if not results:
        return None

    snapshot = results[0]
    if "total_nav" not in snapshot and "_id" not in snapshot:
        return None

    return {
        "timestamp": snapshot.get("_id"),
        "total_nav": snapshot.get("total_nav", 0),
        "unrealized_pnl": snapshot.get("unrealized_pnl", 0),
        "realized_pnl": snapshot.get("realized_pnl", 0),
        "accounts": sorted(account for account in snapshot.get("accounts", []) if account),
        "source": "tws",
        "last_tws_update": snapshot.get("last_tws_update") or snapshot.get("_id"),
    }

def get_report_stats(rtype: NavReportType, account_id: str | None = None):
    """
    Get stats for a single report type.
    Returns dict with {start, end, change, mtm, date} or None.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    normalized_account = _normalize_account_id(account_id)
    base_query = {"ibkr_report_type": rtype.value}
    if normalized_account:
        base_query["account_id"] = normalized_account
    
    # 1. Find the most recent date for this specific report type
    latest_entry = db.ibkr_nav_history.find_one(
        base_query,
        sort=[("_report_date", -1)]
    )
    if not latest_entry:
        return None
        
    target_date = latest_entry["_report_date"]
    
    # 2. Sum up all accounts for that specific date
    pipeline = [
        {"$match": {**base_query, "_report_date": target_date}},
        {"$group": {
            "_id": None,
            "total_start": {"$sum": "$starting_value"},
            "total_end": {"$sum": "$ending_value"},
        }}
    ]
    
    results = list(db.ibkr_nav_history.aggregate(pipeline))
    if not results:
        return None
        
    res = results[0]
    start = res.get("total_start", 0)
    end = res.get("total_end", 0)
    change = ((end - start) / start * 100) if start else 0.0
    
    return {
        "start": start,
        "end": end,
        "mtm": end - start,
        "change": change,
        "date": target_date
    }

def get_nav_history_stats(account_id: str | None = None):
    """
    Calculate NAV Stats using authoritative 'ibkr_nav_history' collection.
    Uses specific IBKR Report Types (1D, 7D, 30D, etc) for precise calculations.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    from app.models import NavReportType
    normalized_account = _normalize_account_id(account_id)
    base_scope = {}
    if normalized_account:
        base_scope["account_id"] = normalized_account

    stats = {
        "current_nav": 0,
        "current_nav_rt": None,
        "change_1d": None, "change_7d": None, "change_30d": None,
        "change_mtd": None, "change_ytd": None, "change_yoy": None, # 1Y
        "change_rt": None,
        "start_1d": None, "start_7d": None, "start_30d": None,
        "start_mtd": None, "start_ytd": None, "start_yoy": None,
        "start_rt": None,
        "history": [],
        "data_source": "flex_eod",
        "last_updated": None,
        "last_updated_rt": None,
        "mtm_rt": None,
        "rt_unrealized_pnl": None,
        "rt_realized_pnl": None,
        "selected_account_id": normalized_account or "ALL",
        "timeframe_meta": {
            "1d": {"value_source": "flex_report", "end_date_source": "flex_close", "end_date": None},
            "7d": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": None},
            "30d": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": None},
            "mtd": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": None},
            "ytd": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": None},
            "yoy": {"value_source": "flex_report", "end_date_source": "flex_report", "end_date": None},
            "rt": {"value_source": "tws_rt", "end_date_source": "tws_rt", "end_date": None},
        },
    }
    
    # helper to aggregate across accounts for the latest available date
    def get_aggregated_stats(rtype: NavReportType):
        # 1. Find the most recent date for this specific report type
        # We sort by _report_date descending to get the "latest batch"
        latest_entry = db.ibkr_nav_history.find_one(
            {"ibkr_report_type": rtype.value, **base_scope},
            sort=[("_report_date", -1)]
        )
        if not latest_entry:
            return None
            
        target_date = latest_entry["_report_date"]
        
        # 2. Sum up all accounts for that specific date
        pipeline = [
            {"$match": {"ibkr_report_type": rtype.value, "_report_date": target_date, **base_scope}},
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
            
        # Inject the date so the caller knows what date this represents
        results[0]["_report_date"] = target_date
        return results[0] # {total_start: X, total_end: Y, _report_date: ...}

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
        
        # Populate Stats
        stats[f"start_{suffix}"] = start
        stats[f"mtm_{suffix}"] = end - start
        stats[f"date_{suffix}"] = agg_res.get("_report_date")
        meta = stats["timeframe_meta"].get(suffix)
        if meta is not None:
            meta["end_date"] = agg_res.get("_report_date")
        
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

    live_snapshot = get_latest_live_nav_snapshot(account_id=normalized_account)
    has_live_snapshot = bool(
        live_snapshot
        and (
            live_snapshot.get("timestamp") is not None
            or live_snapshot.get("last_tws_update") is not None
        )
    )
    live_end_date = live_snapshot.get("last_tws_update") if has_live_snapshot else None
    live_is_recent = _is_recent_live_timestamp(live_end_date)

    if has_live_snapshot:
        live_nav = live_snapshot.get("total_nav")
        stats["current_nav_rt"] = live_nav
        stats["data_source"] = "tws_live"
        stats["last_updated"] = live_snapshot.get("last_tws_update") or live_snapshot.get("timestamp")
        stats["last_updated_rt"] = stats["last_updated"]
        stats["rt_unrealized_pnl"] = live_snapshot.get("unrealized_pnl")
        stats["rt_realized_pnl"] = live_snapshot.get("realized_pnl")
        stats["timeframe_meta"]["rt"]["end_date"] = stats["last_updated_rt"]
        if stats["start_1d"] not in (None, 0):
            stats["start_rt"] = stats["start_1d"]
            stats["mtm_rt"] = live_nav - stats["start_1d"]
            stats["change_rt"] = (stats["mtm_rt"] / stats["start_1d"]) * 100
            stats["timeframe_meta"]["1d"]["value_source"] = "flex_close_plus_rt_current"
        if live_is_recent and live_nav is not None:
            for suffix in ("7d", "30d", "mtd", "ytd", "yoy"):
                start_value = stats.get(f"start_{suffix}")
                if start_value in (None, 0):
                    continue
                mtm_value = live_nav - start_value
                stats[f"mtm_{suffix}"] = mtm_value
                stats[f"change_{suffix}"] = (mtm_value / start_value) * 100
                stats[f"date_{suffix}"] = live_end_date
                stats["timeframe_meta"][suffix]["value_source"] = "tws_rt_calc"
                stats["timeframe_meta"][suffix]["end_date_source"] = "tws_rt"
                stats["timeframe_meta"][suffix]["end_date"] = live_end_date
    elif s_1d:
        stats["last_updated"] = s_1d.get("_report_date")

    # 3. History Graph
    # For the graph, we need a time seriesSum of all accounts per day.
    # We use the NAV_1D report type as the authoritative daily snapshot.
    pipeline = [
        {"$match": {"ibkr_report_type": NavReportType.NAV_1D.value, **base_scope}},
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
            {"$match": {"ibkr_report_type": {"$exists": False}, **base_scope}}, # Old records
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
