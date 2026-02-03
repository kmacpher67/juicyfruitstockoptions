from app.services.expiration_scanner import ExpirationScanner
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)

def run():
    print("Running Expiration Scanner...")
    scanner = ExpirationScanner()
    # Mocking or fetching holdings logic is inside the class.
    # It fetches from DB.
    
    # We need to ensure it uses the same DB connection logic.
    # The ExpirationScanner uses MongoClient(settings.MONGO_URI).
    # Since we set MONGO_URI env var, it should work.
    
    scanner.scan_portfolio_expirations(days_threshold=7)
    print("Scan Complete.")

if __name__ == "__main__":
    run()
