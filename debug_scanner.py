import logging
import sys
from datetime import datetime

# Setup logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_scanner():
    try:
        from app.services.dividend_scanner import DividendScanner
        print("Successfully imported DividendScanner")
        
        scanner = DividendScanner()
        # Test with some large cap dividend stocks
        tickers = ["VZ", "T", "MO", "XOM", "CVX", "KO", "PEP", "ABBV", "JPM", "MAIN", "O"]
        
        print(f"Scanning {len(tickers)} tickers: {tickers}")
        results = scanner.scan_dividend_capture_opportunities(tickers)
        
        print("\nResults:")
        for res in results:
            print(res)
            
    except ImportError as e:
        print(f"ImportError: {e}")
        # Add project root to path if needed (might be running from root)
        sys.path.append('.')
        try:
             from app.services.dividend_scanner import DividendScanner
             test_scanner() # Retry
        except:
             print("Still failed import")
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == "__main__":
    test_scanner()
