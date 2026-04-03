import logging
from typing import List

from stock_live_comparison import StockLiveComparison

def run_stock_live_comparison(tickers: List[str] | None = None, trigger: str = "scheduled") -> dict:
    """Run stock comparison and control report-file creation by trigger.

    trigger values:
    - manual: user clicked "Run Live Comparison" -> always create new report file
    - scheduled: daily scheduler run -> at most one new report file per day
    - sync: background ticker sync/update -> refresh data without creating a new report file
    """
    try:
        if trigger not in {"manual", "scheduled", "sync"}:
            logging.warning(f"Unknown stock comparison trigger '{trigger}', defaulting to scheduled")
            trigger = "scheduled"

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

        if trigger == "sync":
            latest_viable, _ = comp.get_latest_viable_spreadsheet(
                comp.output_dir,
                min_bytes=comp.min_viable_report_bytes,
            )
            if not latest_viable:
                return {
                    "status": "skipped",
                    "reason": "no_viable_existing_report_for_sync",
                    "file": None,
                }

        comp.run(
            force_new_file=(trigger == "manual"),
            allow_create_if_missing=(trigger != "sync"),
        )
        return {"status": "success", "file": comp.filename}
    except Exception as exc:
        logging.exception("Stock live comparison failed")
        return {"status": "error", "error": str(exc)}
