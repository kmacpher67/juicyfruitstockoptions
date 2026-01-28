import logging
from typing import List

from stock_live_comparison import StockLiveComparison

def run_stock_live_comparison(tickers: List[str] | None = None) -> dict:
    """Run the stock live comparison report and return status information."""
    try:
        # If tickers is None, StockLiveComparison will use its internal default list
        comp = StockLiveComparison(tickers)
        comp.run()
        return {"status": "success", "file": comp.filename}
    except Exception as exc:
        logging.exception("Stock live comparison failed")
        return {"status": "error", "error": str(exc)}
