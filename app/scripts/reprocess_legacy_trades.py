import os
import sys
import logging
import glob

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.scripts.import_manual_csv import import_trades_csv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def reprocess_all_legacy():
    legacy_dir = "/home/kenmac/personal/juicyfruitstockoptions/ibkr-legacy-data"
    # Find all CSV files that look like Recent_Trades
    # Use case-insensitive search if needed, but glob is case-sensitive on Linux
    patterns = ["Recent_Trades*.csv", "Recent_trades*.csv"]
    
    csv_files = []
    for pattern in patterns:
        csv_files.extend(glob.glob(os.path.join(legacy_dir, pattern)))
    
    # Remove duplicates if any
    csv_files = sorted(list(set(csv_files)))
    
    if not csv_files:
        logging.error(f"No Recent_Trades CSV files found in {legacy_dir}")
        return

    logging.info(f"Found {len(csv_files)} files to reprocess.")
    
    for filepath in csv_files:
        try:
            import_trades_csv(filepath)
        except Exception as e:
            logging.error(f"Failed to process {filepath}: {e}")

if __name__ == "__main__":
    reprocess_all_legacy()
