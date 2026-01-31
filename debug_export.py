import sys
import os
import io

# Set env var before importing app config
os.environ["MONGO_URI"] = "mongodb://admin:admin123@localhost:27017/?authSource=admin"

sys.path.append(os.getcwd())
try:
    from app.services.export_service import generate_portfolio_csv_content
    print("Testing export...")
    csv_content = generate_portfolio_csv_content()
    print("Export successful, length:", len(csv_content))
    # print("First 100 chars:", csv_content[:100])
except Exception as e:
    print("CRASHED!")
    import traceback
    traceback.print_exc()
