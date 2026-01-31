import sys
import os
os.environ["MONGO_URI"] = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
sys.path.append(os.getcwd())

from fastapi.responses import Response
try:
    from app.services.export_service import generate_portfolio_csv_content
    csv_content = generate_portfolio_csv_content()
    
    r = Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=foo.csv"}
    )
    print("Response created successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
