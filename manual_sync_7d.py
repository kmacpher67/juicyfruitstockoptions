import os
# Force Localhost for host execution BEFORE importing app
os.environ["MONGO_URI"] = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

from app.models import NavReportType
from app.services.ibkr_service import fetch_and_store_nav_report
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

print("Starting Manual 7D Sync (Localhost)...")
try:
    result = fetch_and_store_nav_report(NavReportType.NAV_7D)
    print(f"Sync Result: {result}")
except Exception as e:
    print(f"Sync Failed: {e}")
