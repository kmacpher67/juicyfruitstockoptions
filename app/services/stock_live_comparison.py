import logging
from typing import List

from stock_live_comparison import StockLiveComparison

def run_stock_live_comparison(tickers: List[str] | None = None) -> dict:
    """Run the stock live comparison report and return status information."""
    try:
        # If tickers is None, load default list
        if tickers is None:
             # Auto-discover new portfolio items before running
             try:
                 from app.services.ticker_discovery import discover_and_track_tickers
                 discover_and_track_tickers()
             except Exception as e:
                 logging.error(f"Auto-discovery failed: {e}")

             tickers = StockLiveComparison.get_default_tickers()
        
        comp = StockLiveComparison(tickers)
        comp.run()
        return {"status": "success", "file": comp.filename}
    except Exception as exc:
        logging.exception("Stock live comparison failed")
        return {"status": "error", "error": str(exc)}
