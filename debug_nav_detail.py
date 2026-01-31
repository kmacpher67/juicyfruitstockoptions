
def debug_stats():
    from app.services.portfolio_analysis import get_nav_history_stats
    from app.models import NavReportType
    from pymongo import MongoClient
    from app.config import settings

    # 1. Run the function
    stats = get_nav_history_stats()
    print("--- Calculated Stats ---")
    print(stats)
    
    # 2. Manual Check
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    print("\n--- YTD Detail ---")
    # Get latest date
    latest = db.ibkr_nav_history.find_one({"ibkr_report_type": "NavYTD"}, sort=[("_report_date", -1)])
    if latest:
        d = latest["_report_date"]
        print(f"Latest YTD Date: {d}")
        # Get all accounts for this date
        cursor = db.ibkr_nav_history.find({"ibkr_report_type": "NavYTD", "_report_date": d})
        total_start = 0
        total_end = 0
        print(f"{'Account':<15} {'Start':<15} {'End':<15} {'Change%':<10}")
        for doc in cursor:
            s = doc.get("starting_value", 0)
            e = doc.get("ending_value", 0)
            chg = ((e - s)/s)*100 if s else 0
            print(f"{doc.get('account_id'):<15} {s:<15} {e:<15} {chg:.2f}%")
            total_start += s
            total_end += e
            
        print("-" * 60)
        final_chg = ((total_end - total_start)/total_start)*100 if total_start else 0
        print(f"{'TOTAL':<15} {total_start:<15} {total_end:<15} {final_chg:.2f}%")
        
if __name__ == "__main__":
    try:
        print("Starting debug...", flush=True)
        debug_stats()
    except Exception as e:
        import traceback
        traceback.print_exc()
