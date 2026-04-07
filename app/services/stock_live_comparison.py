import logging
from typing import List
from datetime import datetime, timezone
from pymongo import MongoClient

from stock_live_comparison import StockLiveComparison
from app.config import settings

DEFAULT_STOCK_ANALYSIS_HTTP_SETTINGS = {
    "download_batch_size": 6,
    "batch_pause_sec": 8.0,
    "request_throttle_interval_sec": 1.5,
    "scheduler_sharding_enabled": False,
    "scheduler_shard_size": 25,
    "scheduler_shard_pause_sec": 20.0,
}


def _coerce_stock_analysis_http_settings(doc: dict | None) -> dict:
    payload = dict(DEFAULT_STOCK_ANALYSIS_HTTP_SETTINGS)
    source = doc or {}

    raw_batch_size = source.get("download_batch_size", payload["download_batch_size"])
    raw_batch_pause = source.get("batch_pause_sec", payload["batch_pause_sec"])
    raw_throttle = source.get(
        "request_throttle_interval_sec",
        source.get("min_request_interval_sec", payload["request_throttle_interval_sec"]),
    )
    raw_scheduler_enabled = source.get(
        "scheduler_sharding_enabled",
        payload["scheduler_sharding_enabled"],
    )
    raw_scheduler_shard_size = source.get(
        "scheduler_shard_size",
        payload["scheduler_shard_size"],
    )
    raw_scheduler_shard_pause = source.get(
        "scheduler_shard_pause_sec",
        payload["scheduler_shard_pause_sec"],
    )

    try:
        payload["download_batch_size"] = max(1, int(raw_batch_size))
    except (TypeError, ValueError):
        pass

    try:
        payload["batch_pause_sec"] = max(0.0, float(raw_batch_pause))
    except (TypeError, ValueError):
        pass

    try:
        payload["request_throttle_interval_sec"] = max(0.0, float(raw_throttle))
    except (TypeError, ValueError):
        pass

    if isinstance(raw_scheduler_enabled, str):
        payload["scheduler_sharding_enabled"] = raw_scheduler_enabled.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    else:
        payload["scheduler_sharding_enabled"] = bool(raw_scheduler_enabled)

    try:
        payload["scheduler_shard_size"] = max(1, int(raw_scheduler_shard_size))
    except (TypeError, ValueError):
        pass

    try:
        payload["scheduler_shard_pause_sec"] = max(0.0, float(raw_scheduler_shard_pause))
    except (TypeError, ValueError):
        pass

    return payload


def _load_stock_analysis_http_settings() -> dict:
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        doc = db.system_config.find_one({"_id": "stock_analysis_http_config"}) or {}
        return _coerce_stock_analysis_http_settings(doc)
    except Exception as exc:
        logging.warning("stock analysis http settings fallback to defaults: %s", exc)
        return dict(DEFAULT_STOCK_ANALYSIS_HTTP_SETTINGS)


def _persist_stock_ingest_telemetry(payload: dict) -> None:
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        db.stock_ingest_runs.insert_one(payload)
    except Exception as exc:
        logging.warning("stock ingest telemetry persist failed: %s", exc)

def run_stock_live_comparison(tickers: List[str] | None = None, trigger: str = "scheduled") -> dict:
    """Run stock comparison and control report-file creation by trigger.

    trigger values:
    - manual: user clicked "Run Live Comparison" -> always create new report file
    - scheduled: daily scheduler run -> at most one new report file per day
    - sync: background ticker sync/update -> refresh data without creating a new report file
    """
    try:
        logging.info("run_stock_live_comparison.start trigger=%s explicit_tickers=%s", trigger, bool(tickers))
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
        logging.info("run_stock_live_comparison.ticker_count=%s trigger=%s", len(tickers or []), trigger)

        http_settings = _load_stock_analysis_http_settings()
        logging.info(
            "run_stock_live_comparison.http_settings trigger=%s download_batch_size=%s batch_pause_sec=%s request_throttle_interval_sec=%s",
            trigger,
            http_settings["download_batch_size"],
            http_settings["batch_pause_sec"],
            http_settings["request_throttle_interval_sec"],
        )
        comp = StockLiveComparison(
            tickers,
            download_batch_size=http_settings["download_batch_size"],
            batch_pause_sec=http_settings["batch_pause_sec"],
            min_request_interval_sec=http_settings["request_throttle_interval_sec"],
        )

        if trigger == "sync":
            latest_viable, _ = comp.get_latest_viable_spreadsheet(
                comp.output_dir,
                min_bytes=comp.min_viable_report_bytes,
            )
            if not latest_viable:
                result = {
                    "status": "skipped",
                    "reason": "no_viable_existing_report_for_sync",
                    "file": None,
                }
                _persist_stock_ingest_telemetry(
                    {
                        "job": "stock_live_comparison",
                        "trigger": trigger,
                        "status": "skipped",
                        "reason": "no_viable_existing_report_for_sync",
                        "ticker_count": len(tickers or []),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                logging.info("run_stock_live_comparison.skipped trigger=sync reason=no_viable_existing_report_for_sync")
                return result

        started = datetime.now()
        comp.run(
            force_new_file=(trigger == "manual"),
            allow_create_if_missing=(trigger != "sync"),
        )
        result = {"status": "success", "file": comp.filename, "ticker_count": len(tickers or [])}
        _persist_stock_ingest_telemetry(
            {
                "job": "stock_live_comparison",
                "trigger": trigger,
                "status": "success",
                "file": comp.filename,
                "ticker_count": len(tickers or []),
                "elapsed_sec": round((datetime.now() - started).total_seconds(), 2),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        logging.info(
            "run_stock_live_comparison.success trigger=%s file=%s elapsed_sec=%s",
            trigger,
            comp.filename,
            round((datetime.now() - started).total_seconds(), 2),
        )
        return result
    except Exception as exc:
        logging.exception("Stock live comparison failed")
        _persist_stock_ingest_telemetry(
            {
                "job": "stock_live_comparison",
                "trigger": trigger,
                "status": "error",
                "error": str(exc),
                "ticker_count": len(tickers or []),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return {"status": "error", "error": str(exc)}
