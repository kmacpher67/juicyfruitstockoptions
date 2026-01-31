from app.services.ibkr_service import parse_csv_nav
import os

# Path regarding Container Root (/app)
# Script is in /app/app/scripts/
# File is in /app/app/NAV...
file_path = "/app/app/NAV-7day-2026-01-29.csv"

if os.path.exists(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    # It expects raw bytes sometimes? parse_csv_nav takes string.
    parse_csv_nav(content)
    print(f"Imported {file_path}")
else:
    print(f"File {file_path} not found. CWD is {os.getcwd()}")
    print(f"Listing /app/app: {os.listdir('/app/app') if os.path.exists('/app/app') else 'Not Found'}")
