from pymongo import MongoClient
from app.models import NavReportType
import json
from datetime import datetime

MONGO_URI = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client.get_default_database("stock_analysis")
    
    reports = ["NAVMTD", "NAVYTD"]
    
    print("--- NAV History Inspection ---")
    for r in reports:
        # Get top 3 latest by report date
        cursor = db.ibkr_nav_history.find(
            {"ibkr_report_type": r}
        ).sort("_report_date", -1).limit(3)
        
        print(f"\nReport: {r}")
        for doc in cursor:
            print(f"  ReportDate: {doc.get('_report_date')} | ToDate: {doc.get('to_date')} | Ingested: {doc.get('_ingested_at')}")

    print("\n--- Raw Reports Inspection ---")
    for r in reports:
        latest = db.ibkr_raw_flex_reports.find_one(
             {"ibkr_report_type": r},
             sort=[("_ingested_at", -1)]
        )
        if latest:
             print(f"\nReport: {r} (RAW)")
             print(f"  Ingested: {latest.get('_ingested_at')}")
             # Print content snippet if available
             content = latest.get("content")
             if content:
                 try:
                     text = content.decode('utf-8')[:500] if isinstance(content, bytes) else str(content)[:500]
                     print(f"  Snippet: {text}")
                 except: 
                     print("  Snippet: (binary/unreadable)")
        else:
            print(f"\nReport: {r} (RAW) - None Found")

except Exception as e:
    print(f"Error: {e}")
