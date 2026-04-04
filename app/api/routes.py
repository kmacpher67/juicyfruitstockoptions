from collections import defaultdict
from datetime import timedelta, datetime, timezone
import re
from typing import Annotated, List
from zoneinfo import ZoneInfo
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import MongoClient
import yfinance as yf
import pandas as pd

from app.auth.dependencies import get_current_active_user
from app.auth.utils import create_access_token, verify_password, get_password_hash
from app.config import settings
from app.models import Token, User, StockRecord, IBKRConfig, IBKRStatus, NavReportType
from app.services.portfolio_fixer import run_portfolio_fixer
from app.services.stock_live_comparison import run_stock_live_comparison
from app.services.ibkr_service import fetch_and_store_nav_report
from app.database import get_db
from app.services.signal_service import SignalService
from app.services.ibkr_tws_service import get_ibkr_tws_service
from app.services.data_refresh_queue import get_data_refresh_queue
from app.utils.logging_config import log_endpoint

router = APIRouter()


import logging
logger = logging.getLogger(__name__)


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _normalize_ticker_symbol(raw_symbol: str | None) -> str:
    value = str(raw_symbol or "").strip().upper()
    if not value:
        return ""

    # Option-like display symbols can include spaces (e.g. "AMD 2026-04-02 202.5 Call").
    value = value.split()[0]
    occ_match = re.match(r"^([A-Z]{1,6})\d{6}[CP]\d+", value)
    if occ_match:
        return occ_match.group(1)
    return value


def _format_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _parse_datetime_utc(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if parsed is None or pd.isna(parsed):
        return None
    return parsed.to_pydatetime().astimezone(timezone.utc)


def _is_us_equity_market_session(now_utc: datetime | None = None) -> bool:
    now_utc = now_utc or datetime.now(timezone.utc)
    et_now = now_utc.astimezone(ZoneInfo("America/New_York"))
    if et_now.weekday() >= 5:
        return False
    open_et = et_now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_et = et_now.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_et <= et_now <= close_et


def _evaluate_stock_data_freshness(stock: dict | None, tier: str = "mixed") -> dict:
    if not stock:
        return {
            "data_source": "stock_data_db",
            "last_updated": None,
            "is_stale": True,
            "stale_reason": "data_missing",
            "refresh_queued": False,
        }

    last_updated_raw = stock.get("_last_persisted_at") or stock.get("Last Update")
    last_updated_dt = _parse_datetime_utc(last_updated_raw)
    if last_updated_dt is None:
        return {
            "data_source": str(stock.get("source") or "stock_data_db"),
            "last_updated": None,
            "is_stale": True,
            "stale_reason": "missing_last_updated",
            "refresh_queued": False,
        }

    now_utc = datetime.now(timezone.utc)
    is_market_session = _is_us_equity_market_session(now_utc)
    thresholds = {
        "price": timedelta(minutes=15 if is_market_session else 12 * 60),
        "mixed": timedelta(minutes=30 if is_market_session else 24 * 60),
        "profile": timedelta(hours=24 if is_market_session else 24 * 7),
    }
    threshold = thresholds.get(tier, thresholds["mixed"])
    age = now_utc - last_updated_dt
    is_stale = age > threshold
    stale_reason = None
    if is_stale:
        stale_reason = f"older_than_{int(threshold.total_seconds() // 60)}m"

    return {
        "data_source": str(stock.get("source") or "stock_data_db"),
        "last_updated": _format_utc_iso(last_updated_dt),
        "is_stale": is_stale,
        "stale_reason": stale_reason,
        "refresh_queued": False,
    }


def _queue_stock_refresh_if_stale(background_tasks: BackgroundTasks | None, symbol: str, freshness: dict) -> None:
    if not background_tasks or not freshness.get("is_stale"):
        return
    queued = get_data_refresh_queue().enqueue_stock_sync(
        background_tasks=background_tasks,
        symbol=symbol,
        refresh_fn=run_stock_live_comparison,
    )
    freshness["refresh_queued"] = bool(queued)
    if not queued and not freshness.get("stale_reason"):
        freshness["stale_reason"] = "refresh_cooldown_active"


def _persist_signal_payload(db, ticker: str, kalman: dict, markov: dict, advice: dict) -> None:
    persisted_at = _format_utc_iso(datetime.now(timezone.utc))
    payload = {
        "kalman": kalman,
        "markov": markov,
        "advice": advice,
        "_persisted_at": persisted_at,
    }
    db.stock_data.update_one(
        {"Ticker": ticker},
        {
            "$set": {
                "signals": payload,
                "_signals_persisted_at": persisted_at,
            }
        },
        upsert=True,
    )


def _find_stock_data_by_symbol(db, raw_symbol: str) -> tuple[dict | None, dict, str]:
    symbol = _normalize_ticker_symbol(raw_symbol)
    if not symbol:
        return None, {}, symbol

    exact_query = {"Ticker": symbol}
    stock = db.stock_data.find_one(exact_query, {"_id": 0})
    if stock:
        return stock, exact_query, symbol

    escaped = re.escape(symbol)
    relaxed_query = {"Ticker": {"$regex": rf"^\s*{escaped}\s*$", "$options": "i"}}
    stock = db.stock_data.find_one(relaxed_query, {"_id": 0})
    if stock:
        return stock, relaxed_query, _normalize_ticker_symbol(stock.get("Ticker") or symbol)

    return None, exact_query, symbol


def _canonical_security_type(row: dict) -> str:
    candidates = [
        row.get("security_type"),
        row.get("asset_class"),
        row.get("AssetClass"),
        row.get("secType"),
        row.get("sec_type"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate).upper()

    symbol = str(row.get("symbol") or "")
    local_symbol = str(row.get("local_symbol") or "")
    contract_hint = " ".join(part for part in [symbol, local_symbol] if part)
    if re.search(r"\d{6}[CP]\d+", contract_hint):
        return "OPT"
    return "STK"


def _extract_option_fields(row: dict) -> tuple[str | None, str | None, float | None]:
    expiry = row.get("expiry") or row.get("last_trade_date") or row.get("lastTradeDateOrContractMonth")
    right = row.get("right")
    strike = _safe_float(row.get("strike"))

    local_symbol = str(row.get("local_symbol") or row.get("localSymbol") or "")
    if local_symbol:
        match = re.search(r"(\d{6})([CP])(\d+)$", local_symbol.strip())
        if match:
            expiry = expiry or match.group(1)
            right = right or match.group(2)
            if strike is None:
                strike = int(match.group(3)) / 1000.0

    symbol = str(row.get("symbol") or "")
    if symbol and (expiry is None or right is None or strike is None):
        match = re.search(r"(\d{6})([CP])(\d+)", symbol)
        if match:
            expiry = expiry or match.group(1)
            right = right or match.group(2)
            if strike is None:
                strike = int(match.group(3)) / 1000.0

    return expiry, right, strike


def _extract_option_underlying(row: dict) -> str | None:
    explicit = row.get("underlying_symbol") or row.get("underlying")
    if explicit:
        return str(explicit).strip()

    local_symbol = str(row.get("local_symbol") or row.get("localSymbol") or "").strip()
    if local_symbol:
        root = local_symbol[:6].strip()
        if root:
            return root

    symbol = str(row.get("symbol") or "").strip()
    if symbol:
        occ_match = re.match(r"^([A-Z]{1,6})\s+\d{6}[CP]\d+", symbol)
        if occ_match:
            return occ_match.group(1).strip()

    return symbol or None


def _format_option_expiry(expiry: str | None) -> str | None:
    if not expiry:
        return None

    value = str(expiry).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y%m", "%Y-%m"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _build_display_symbol(row: dict, security_type: str) -> str:
    symbol = str(row.get("symbol") or "").strip()
    underlying = str(_extract_option_underlying(row) or symbol).strip()

    if security_type not in {"OPT", "FOP"}:
        return symbol or underlying

    expiry, right, strike = _extract_option_fields(row)
    expiry_label = _format_option_expiry(expiry)
    right_label = {"C": "Call", "P": "Put"}.get(str(right or "").upper(), str(right or "").upper() or None)
    strike_label = f"{strike:g}" if strike is not None else None

    parts = [part for part in [underlying or symbol, expiry_label, strike_label, right_label] if part]
    if parts:
        return " ".join(parts)
    return symbol or underlying


def _is_short_call_position(row: dict) -> bool:
    security_type = _canonical_security_type(row)
    if security_type not in {"OPT", "FOP"}:
        return False

    quantity = _safe_float(row.get("quantity"))
    if quantity is None:
        quantity = _safe_float(row.get("position"))
    if quantity is None or quantity >= 0:
        return False

    right = str(row.get("right") or "").strip().upper()
    if right == "C":
        return True

    _, parsed_right, _ = _extract_option_fields(row)
    if str(parsed_right or "").strip().upper() == "C":
        return True

    local_symbol = str(row.get("local_symbol") or row.get("localSymbol") or "")
    symbol = str(row.get("symbol") or "")
    return bool(re.search(r"\d{6}C\d+", local_symbol) or re.search(r"\d{6}C\d+", symbol))


def _resolve_coverage_status(shares, short_calls):
    """Return coverage status and mismatch flag as defined in requirements."""
    shares = float(shares or 0)
    short_calls = float(short_calls or 0)
    covered_calls = abs(short_calls)

    if shares == covered_calls:
        return "Covered", False
    if shares > covered_calls:
        return "Uncovered", True
    if shares < covered_calls:
        return "Naked", True
    return "", False


def _is_flat_position_row(row: dict) -> bool:
    quantity = _safe_float(row.get("quantity"))
    if quantity is None:
        quantity = _safe_float(row.get("position"))
    if quantity is None:
        return True
    return abs(quantity) < 1e-9


def _normalize_order_action(raw_value):
    value = str(raw_value or "").strip().upper()
    if value in {"BOT", "BUY"}:
        return "BUY"
    if value in {"SLD", "SELL"}:
        return "SELL"
    return value


def _is_active_pending_order(row: dict) -> bool:
    status = str(row.get("status") or "").strip()
    if status in {"Filled", "Cancelled", "ApiCancelled", "Inactive"}:
        return False

    remaining = _safe_float(row.get("remaining_quantity"))
    if remaining is None:
        remaining = _safe_float(row.get("total_quantity"))
    if remaining is not None and remaining <= 0:
        return False

    return True


def _is_call_order(row: dict) -> bool:
    security_type = _canonical_security_type(row)
    if security_type not in {"OPT", "FOP"}:
        return False

    right = str(row.get("right") or "").strip().upper()
    if right == "C":
        return True

    _, parsed_right, _ = _extract_option_fields(row)
    return str(parsed_right or "").strip().upper() == "C"


def _normalize_order_row(order: dict) -> dict:
    normalized = dict(order)
    security_type = _canonical_security_type(normalized)
    account_id = normalized.get("account_id") or normalized.get("account") or "UNKNOWN"
    underlying_symbol = _extract_option_underlying(normalized) if security_type in {"OPT", "FOP"} else (
        normalized.get("underlying_symbol") or normalized.get("underlying") or normalized.get("symbol")
    )
    action = _normalize_order_action(normalized.get("action"))
    status = str(normalized.get("status") or "").strip()
    total_quantity = _safe_float(normalized.get("total_quantity"))
    filled_quantity = _safe_float(normalized.get("filled_quantity"))
    remaining_quantity = _safe_float(normalized.get("remaining_quantity"))
    if remaining_quantity is None and total_quantity is not None and filled_quantity is not None:
        remaining_quantity = max(total_quantity - filled_quantity, 0.0)
    if remaining_quantity is None:
        remaining_quantity = total_quantity

    normalized.update(
        {
            "account_id": account_id,
            "security_type": security_type,
            "asset_class": security_type,
            "secType": security_type,
            "underlying_symbol": underlying_symbol,
            "display_symbol": _build_display_symbol(normalized, security_type),
            "action": action,
            "status": status,
            "total_quantity": total_quantity,
            "filled_quantity": filled_quantity,
            "remaining_quantity": remaining_quantity,
            "is_active": _is_active_pending_order(normalized),
            "limit_price": _safe_float(normalized.get("limit_price")),
            "aux_price": _safe_float(normalized.get("aux_price")),
            "avg_fill_price": _safe_float(normalized.get("avg_fill_price")),
            "last_fill_price": _safe_float(normalized.get("last_fill_price")),
            "strike": _safe_float(normalized.get("strike")),
            "multiplier": _safe_float(normalized.get("multiplier")),
            "source": normalized.get("source") or "unknown",
            "last_update": (
                normalized.get("last_update")
                or normalized.get("last_tws_update")
                or normalized.get("source_as_of")
            ),
        }
    )
    return normalized


def _market_context_for_ticker(db, ticker: str | None) -> dict:
    if not ticker:
        return {}
    doc = db.stock_data.find_one({"Ticker": ticker}, {"_id": 0}) or {}

    def _safe_percent(value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "").replace(",", "")
            return _safe_float(cleaned)
        return _safe_float(value)

    return {
        "last_price": _safe_float(doc.get("Current Price")),
        "day_change_pct": _safe_percent(doc.get("1D % Change")),
        "yoy_price_pct": _safe_percent(doc.get("YoY Price %")),
        "call_put_skew": _safe_float(doc.get("Call/Put Skew")),
        "tsmom_60": _safe_float(doc.get("TSMOM_60")),
        "ma_200": _safe_float(doc.get("MA_200")),
        "ema_20": _safe_float(doc.get("EMA_20")),
        "hma_20": _safe_float(doc.get("HMA_20")),
        "div_yield": _safe_percent(doc.get("Div Yield")),
    }


def _load_pending_order_summaries(db, coverage_by_account) -> dict[tuple[str, str], dict]:
    try:
        orders = list(db.ibkr_orders.find({"source": {"$in": ["tws_open_order", "flex_order_history"]}}, {"_id": 0}))
    except Exception:
        orders = []

    pending_by_account = defaultdict(
        lambda: {
            "pending_order_count": 0,
            "pending_sell_call_contracts": 0.0,
            "pending_sell_call_shares": 0.0,
            "pending_buy_call_contracts": 0.0,
            "pending_buy_call_shares": 0.0,
            "has_unknown_orders": False,
        }
    )

    for order in orders:
        if not _is_active_pending_order(order):
            continue

        account_id = order.get("account_id") or order.get("account") or "UNKNOWN"
        underlying = _extract_option_underlying(order) or order.get("symbol")
        if not underlying:
            continue

        key = (account_id, underlying)
        summary = pending_by_account[key]
        summary["pending_order_count"] += 1

        if not _is_call_order(order):
            summary["has_unknown_orders"] = True
            continue

        remaining_quantity = _safe_float(order.get("remaining_quantity"))
        if remaining_quantity is None:
            remaining_quantity = _safe_float(order.get("total_quantity"))
        if remaining_quantity is None:
            summary["has_unknown_orders"] = True
            continue

        multiplier = _safe_float(order.get("multiplier"))
        if multiplier is None:
            multiplier = 100.0

        action = _normalize_order_action(order.get("action"))
        contract_count = abs(float(remaining_quantity))
        share_count = contract_count * multiplier

        if action == "SELL":
            summary["pending_sell_call_contracts"] += contract_count
            summary["pending_sell_call_shares"] += share_count
        elif action == "BUY":
            summary["pending_buy_call_contracts"] += contract_count
            summary["pending_buy_call_shares"] += share_count
        else:
            summary["has_unknown_orders"] = True

    result = {}
    all_keys = set(coverage_by_account.keys()) | set(pending_by_account.keys())
    for key in all_keys:
        current = coverage_by_account.get(key, {"shares": 0.0, "short_calls": 0.0})
        pending = pending_by_account.get(key, {})

        shares = float(current.get("shares") or 0.0)
        short_call_shares = float(current.get("short_calls") or 0.0)
        pending_sell_shares = float(pending.get("pending_sell_call_shares") or 0.0)
        pending_buy_shares = float(pending.get("pending_buy_call_shares") or 0.0)
        pending_sell_contracts = float(pending.get("pending_sell_call_contracts") or 0.0)
        pending_buy_contracts = float(pending.get("pending_buy_call_contracts") or 0.0)
        pending_order_count = int(pending.get("pending_order_count") or 0)

        projected_short_call_shares = max(0.0, short_call_shares - pending_buy_shares + pending_sell_shares)
        current_status, _ = _resolve_coverage_status(shares, short_call_shares)
        projected_status, _ = _resolve_coverage_status(shares, projected_short_call_shares)

        pending_roll_contracts = min(pending_buy_contracts, pending_sell_contracts)
        uncovered_shares_now = max(0.0, shares - short_call_shares)

        if pending_order_count == 0:
            effect = "none"
        elif pending_buy_contracts > 0 and pending_sell_contracts > 0:
            effect = "rolling"
        elif pending_buy_contracts > 0:
            effect = "buying_to_close"
        elif pending_sell_contracts > 0:
            if shares <= 0 or (short_call_shares + pending_sell_shares) > shares:
                effect = "increasing_naked_risk"
            else:
                effect = "covering_uncovered"
        elif pending.get("has_unknown_orders"):
            effect = "unknown"
        else:
            effect = "none"

        result[key] = {
            "pending_order_count": pending_order_count,
            "pending_order_effect": effect,
            "coverage_status_if_filled": projected_status or current_status,
            "pending_cover_shares": pending_sell_shares,
            "pending_cover_contracts": pending_sell_contracts,
            "pending_buy_to_close_contracts": pending_buy_contracts,
            "pending_roll_contracts": pending_roll_contracts,
            "uncovered_shares_now": uncovered_shares_now,
        }

    return result


def _portfolio_row_key(row: dict) -> tuple:
    security_type = _canonical_security_type(row)
    account_id = row.get("account_id") or row.get("account") or "UNKNOWN"

    if security_type in {"OPT", "FOP"}:
        expiry, right, strike = _extract_option_fields(row)
        underlying = str(_extract_option_underlying(row) or row.get("symbol") or "").strip().upper()
        if underlying or expiry or right or strike is not None:
            return (
                account_id,
                security_type,
                underlying,
                _format_option_expiry(expiry),
                str(right or "").upper(),
                strike,
            )

    symbol = str(row.get("symbol") or row.get("local_symbol") or "").strip().upper()
    underlying = str(row.get("underlying_symbol") or row.get("underlying") or "").strip().upper()
    return (account_id, security_type, underlying or symbol, symbol)


def _normalize_portfolio_row(row: dict) -> dict:
    normalized = dict(row)
    security_type = _canonical_security_type(normalized)
    underlying_symbol = _extract_option_underlying(normalized) if security_type in {"OPT", "FOP"} else (
        normalized.get("underlying_symbol") or normalized.get("underlying") or normalized.get("symbol")
    )
    quantity = _safe_float(normalized.get("quantity"))
    if quantity is None:
        quantity = _safe_float(normalized.get("position"))

    market_price = _safe_float(normalized.get("market_price"))
    if market_price is None:
        market_price = _safe_float(normalized.get("mark_price"))
    if market_price is None:
        market_price = _safe_float(normalized.get("marketPrice"))
    if market_price is None:
        market_price = _safe_float(normalized.get("last_price"))

    market_value = _safe_float(normalized.get("market_value"))
    if market_value is None:
        market_value = _safe_float(normalized.get("position_value"))
    if market_value is None:
        market_value = _safe_float(normalized.get("marketValue"))
    if market_value is None:
        market_value = _safe_float(normalized.get("positionValue"))
    if market_value is None and market_price is not None and quantity is not None:
        multiplier = _safe_float(normalized.get("multiplier"))
        if multiplier is None:
            multiplier = 100.0 if security_type in {"OPT", "FOP"} else 1.0
        market_value = market_price * quantity * multiplier

    cost_basis = _safe_float(normalized.get("cost_basis"))
    if cost_basis is None:
        cost_basis = _safe_float(normalized.get("avg_cost"))
    if cost_basis is None:
        cost_basis = _safe_float(normalized.get("averageCost"))
    if cost_basis is None:
        cost_basis = _safe_float(normalized.get("avgCost"))

    unrealized_pnl = _safe_float(normalized.get("unrealized_pnl"))
    if unrealized_pnl is None:
        unrealized_pnl = _safe_float(normalized.get("unrealizedPnL"))
    if unrealized_pnl is None:
        unrealized_pnl = _safe_float(normalized.get("unrealizedPNL"))
    percent_of_nav = _safe_float(normalized.get("percent_of_nav"))
    if percent_of_nav is not None and percent_of_nav > 1:
        percent_of_nav = percent_of_nav / 100.0

    account_id = normalized.get("account_id") or normalized.get("account")
    display_symbol = _build_display_symbol(normalized, security_type)
    description = (
        normalized.get("description")
        or normalized.get("Description")
        or normalized.get("display_symbol")
        or display_symbol
        or normalized.get("local_symbol")
        or normalized.get("localSymbol")
        or normalized.get("symbol")
    )
    normalized.update(
        {
            "account_id": account_id,
            "quantity": quantity,
            "market_price": market_price,
            "market_value": market_value,
            "cost_basis": cost_basis,
            "unrealized_pnl": unrealized_pnl,
            "percent_of_nav": percent_of_nav,
            "security_type": security_type,
            "asset_class": security_type,
            "secType": security_type,
            "underlying_symbol": underlying_symbol,
            "display_symbol": display_symbol,
            "description": description,
        }
    )
    return normalized


def _latest_holdings_query_for_source(db, source: str | None) -> dict | None:
    if source == "tws":
        latest = db.ibkr_holdings.find_one({"source": "tws"}, sort=[("date", -1)])
    elif source == "flex":
        latest = db.ibkr_holdings.find_one({"source": "flex"}, sort=[("date", -1)])
        if not latest:
            latest = db.ibkr_holdings.find_one({"source": {"$exists": False}}, sort=[("date", -1)])
    else:
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])

    if not latest:
        return None

    snapshot_id = latest.get("snapshot_id")
    if snapshot_id:
        query = {"snapshot_id": snapshot_id}
    else:
        query = {"report_date": latest.get("report_date")}

    if source == "tws":
        query["source"] = "tws"
    elif source == "flex":
        if latest.get("source") == "flex":
            query["source"] = "flex"
        else:
            query["source"] = {"$exists": False}

    return query


def _merge_portfolio_rows(base_row: dict, incoming_row: dict) -> dict:
    merged = dict(base_row)
    incoming_source = incoming_row.get("source")
    merged_sources = set(merged.get("merged_sources") or [])
    if merged.get("source"):
        merged_sources.add(merged["source"])
    if incoming_source:
        merged_sources.add(incoming_source)

    if incoming_source == "tws":
        preferred_fields = [
            "quantity",
            "market_price",
            "market_value",
            "unrealized_pnl",
            "percent_of_nav",
            "last_tws_update",
            "date",
            "source",
        ]
        for field in preferred_fields:
            value = incoming_row.get(field)
            if value is not None:
                merged[field] = value

    for field, value in incoming_row.items():
        if field == "merged_sources":
            continue
        if merged.get(field) is None and value is not None:
            merged[field] = value

    if merged_sources:
        merged["merged_sources"] = sorted(merged_sources)
    return merged


def _load_portfolio_holdings_rows(db) -> list[dict]:
    live_query = _latest_holdings_query_for_source(db, "tws")
    flex_query = _latest_holdings_query_for_source(db, "flex")

    row_groups: list[list[dict]] = []
    seen_queries: set[tuple] = set()
    for query in [live_query, flex_query]:
        if not query:
            continue
        key = tuple(sorted((k, str(v)) for k, v in query.items()))
        if key in seen_queries:
            continue
        seen_queries.add(key)
        row_groups.append(list(db.ibkr_holdings.find(query, {"_id": 0})))

    if not row_groups:
        fallback_query = _latest_holdings_query_for_source(db, None)
        if not fallback_query:
            return []
        row_groups.append(list(db.ibkr_holdings.find(fallback_query, {"_id": 0})))

    merged_rows: dict[tuple, dict] = {}
    for rows in row_groups:
        for raw_row in rows:
            normalized = _normalize_portfolio_row(raw_row)
            key = _portfolio_row_key(normalized)
            if key in merged_rows:
                merged_rows[key] = _merge_portfolio_rows(merged_rows[key], normalized)
            else:
                merged_rows[key] = normalized

    return list(merged_rows.values())

@router.post("/token", response_model=Token)
@log_endpoint
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Authenticate against MongoDB
    logger.debug(f"Login attempt for user: {form_data.username}")
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    try:
        user = db.users.find_one({"username": form_data.username})
        
        if not user:
             logger.warning(f"Login failed: User {form_data.username} not found")
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not verify_password(form_data.password, user["hashed_password"]):
             logger.warning(f"Login failed: Password mismatch for {form_data.username}")
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login DB error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Login Error")

@router.get("/users/me", response_model=User)
@log_endpoint
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

# --- Secured Endpoints ---

@router.get("/stocks", response_model=List[StockRecord])
@log_endpoint
async def get_stocks(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Fetch all stock records from MongoDB.
    """
    try:
        # Connect to Mongo (Connection pooling is handled by driver, simple connect here is fine for now)
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        collection = db["stock_data"]
        
        # Fetch all records, exclude internal Mongo ID
        cursor = collection.find({}, {"_id": 0})
        results = list(cursor)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/run/portfolio-fixer")
@log_endpoint
def run_portfolio_fixer_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return run_portfolio_fixer()

from fastapi import BackgroundTasks
from app.jobs import (
    create_job,
    get_job,
    get_latest_job,
    list_jobs,
    touch_job,
    update_job_status,
    JobStatus,
    Job,
)


def background_job_wrapper(job_id: str, func, timeout_seconds: int | None = None):
    """Wrapper to run a function and update job status."""
    try:
        update_job_status(job_id, JobStatus.RUNNING, message="running")
        touch_job(job_id, message="running")
        # Execute directly in FastAPI BackgroundTasks context. Avoid nested executor
        # timeout wrappers here because they can deadlock shutdown/wait paths and stall
        # the API process, which surfaces in UI as global "Loading..." hang.
        result = func()
        update_job_status(job_id, JobStatus.COMPLETED, result=result, message="completed")
    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, error=str(e), message="failed")

@router.get("/jobs/{job_id}", response_model=Job)
@log_endpoint
def get_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    job = get_job(job_id)
    if not job:
          raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/run/stock-live-comparison")
@log_endpoint
def run_stock_live_comparison_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    stale_minutes = 90
    stale_cutoff = datetime.now() - timedelta(minutes=stale_minutes)
    for job in list_jobs(job_type="stock_live_comparison"):
        if job.status != JobStatus.RUNNING:
            continue
        heartbeat = job.heartbeat_at or job.started_at or job.created_at
        if heartbeat and heartbeat.replace(tzinfo=None) < stale_cutoff:
            update_job_status(
                job.id,
                JobStatus.FAILED,
                error=f"Marked stale by watchdog after {stale_minutes}m without heartbeat.",
                message="stale_watchdog_failed",
            )
            logging.warning("Marked stale stock-live-comparison job as failed: %s", job.id)

    # Create Job
    job = create_job(job_type="stock_live_comparison", name="stock-live-comparison")
    
    # Add to Background Tasks
    background_tasks.add_task(
        background_job_wrapper,
        job.id,
        lambda: run_stock_live_comparison(trigger="manual"),
    )
    
    return {"job_id": job.id, "status": "queued"}


@router.get("/jobs/latest/stock-live-comparison", response_model=Job)
@log_endpoint
def get_latest_stock_live_job(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    job = get_latest_job(job_type="stock_live_comparison")
    if not job:
        raise HTTPException(status_code=404, detail="No stock-live-comparison jobs found")
    return job

# --- Scheduler Config Endpoints ---

from pydantic import BaseModel
class ScheduleConfig(BaseModel):
    hour: int
    minute: int

@router.get("/schedule", response_model=ScheduleConfig)
@log_endpoint
def get_schedule(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    from app.scheduler.jobs import get_schedule_config
    return get_schedule_config()

@router.post("/schedule")
@log_endpoint
def update_schedule(
    config: ScheduleConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    from app.scheduler.jobs import reschedule_daily_job
    try:
        reschedule_daily_job(config.hour, config.minute)
        return {"status": "success", "message": f"Rescheduled to {config.hour:02d}:{config.minute:02d}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- User Settings Persistence ---

class UserSettings(BaseModel):
    pageSize: int = 100
    sortColumn: str = "Ticker"
    sortOrder: str = "asc"

@router.get("/settings", response_model=UserSettings)
@log_endpoint
def get_user_settings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        # Fetch settings for this user
        doc = db.user_settings.find_one({"username": current_user.username})
        if doc:
            return UserSettings(**doc)
        # Defaults
        return UserSettings()
    except Exception as e:
        # Default fallback on error
        return UserSettings()

@router.post("/settings")
@log_endpoint
def save_user_settings(
    user_settings: UserSettings,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client["stock_analysis"]
        db.user_settings.update_one(
            {"username": current_user.username},
            {"$set": user_settings.dict()},
            upsert=True
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

class AccountConfig(BaseModel):
    account_id: str
    taxable: bool = False
    alias: str = ""

@router.get("/settings/accounts", response_model=List[AccountConfig])
@log_endpoint
def get_account_settings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """List all known accounts and their settings."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Discover Accounts from Holdings & NAV
    # Use distinct to find all account IDs present in data
    known_accounts = set(db.ibkr_holdings.distinct("account_id"))
    known_accounts.update(db.ibkr_nav_history.distinct("account_id"))
    
    # 2. Fetch Metadata
    meta_doc = db.system_config.find_one({"_id": "account_metadata"}) or {}
    meta = meta_doc.get("accounts", {})
    
    results = []
    for acc in sorted([a for a in known_accounts if a]): # Filter None
        cfg = meta.get(acc, {})
        results.append(AccountConfig(
            account_id=acc,
            taxable=cfg.get("taxable", False),
            alias=cfg.get("alias", "")
        ))
        
    return results

@router.post("/settings/accounts")
@log_endpoint
def update_account_settings(
    configs: List[AccountConfig],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")
         
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Convert list to dict map for storage
    meta_map = {c.account_id: {"taxable": c.taxable, "alias": c.alias} for c in configs}
    
    db.system_config.update_one(
        {"_id": "account_metadata"},
        {"$set": {"accounts": meta_map}},
        upsert=True
    )
    return {"status": "success"}

@router.get("/reports", response_model=List[str])
@log_endpoint
async def list_reports(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """List all available Excel reports."""
    import os
    report_dir = "report-results"
    if not os.path.exists(report_dir):
        return []
    files = [f for f in os.listdir(report_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(report_dir, x)), reverse=True)
    return files

@router.get("/reports/{filename}/data")
@log_endpoint
async def get_report_data(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Read a specific Excel file and return as JSON for the grid."""
    import os
    import pandas as pd
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        # Read Excel using pandas
        # Ensure we read the correct engine
        df = pd.read_excel(report_path, engine='openpyxl')
        
        # Handle NaN/Inf for JSON compliance
        df = df.replace({float('nan'): None, float('inf'): None, float('-inf'): None})
        
        # Convert to list of dicts
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {str(e)}")

@router.get("/reports/{filename}/download")
@log_endpoint
async def download_report(
    filename: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Download a specific Excel report."""
    import os
    from fastapi.responses import FileResponse
    
    report_path = os.path.join("report-results", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(report_path, filename=filename)

# --- IBKR Integrations (Admin Only) ---

@router.get("/integrations/ibkr", response_model=IBKRStatus)
@log_endpoint
def get_ibkr_status(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    config = db.system_config.find_one({"_id": "ibkr_config"})
    
    if not config:
        return IBKRStatus(configured=False)
        
    token = config.get("flex_token", "")
    masked = f"{token[:4]}...{token[-4:]}" if token and len(token) > 8 else "****"
    
    last_sync_doc = db.system_config.find_one({"_id": "ibkr_last_sync"})
    last_sync = None
    if last_sync_doc:
        last_sync = {
            "status": last_sync_doc.get("status"),
            "message": last_sync_doc.get("message"),
            "timestamp": last_sync_doc.get("timestamp")
        }
    
    return IBKRStatus(
        configured=True,
        flex_token_masked=masked,
        query_id_holdings=config.get("query_id_holdings"),
        query_id_trades=config.get("query_id_trades"),
        query_id_orders=config.get("query_id_orders"),
        query_id_nav=config.get("query_id_nav"),
        query_id_nav_1d=config.get("query_id_nav_1d"),
        query_id_nav_7d=config.get("query_id_nav_7d"),
        query_id_nav_30d=config.get("query_id_nav_30d"),
        query_id_nav_mtd=config.get("query_id_nav_mtd"),
        query_id_nav_ytd=config.get("query_id_nav_ytd"),
        query_id_nav_1y=config.get("query_id_nav_1y"),
        query_id_dividends=config.get("query_id_dividends"),
        last_sync=last_sync
    )

@router.post("/integrations/ibkr")
@log_endpoint
def update_ibkr_config(
    config: IBKRConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    update_data = {}
    if config.flex_token:
        update_data["flex_token"] = config.flex_token
    if config.query_id_holdings:
        update_data["query_id_holdings"] = config.query_id_holdings
    if config.query_id_trades:
        update_data["query_id_trades"] = config.query_id_trades
    if config.query_id_orders:
        update_data["query_id_orders"] = config.query_id_orders
    if config.query_id_nav:
        update_data["query_id_nav"] = config.query_id_nav
    if config.query_id_nav_1d: update_data["query_id_nav_1d"] = config.query_id_nav_1d
    if config.query_id_nav_7d: update_data["query_id_nav_7d"] = config.query_id_nav_7d
    if config.query_id_nav_30d: update_data["query_id_nav_30d"] = config.query_id_nav_30d
    if config.query_id_nav_mtd: update_data["query_id_nav_mtd"] = config.query_id_nav_mtd
    if config.query_id_nav_ytd: update_data["query_id_nav_ytd"] = config.query_id_nav_ytd
    if config.query_id_nav_1y: update_data["query_id_nav_1y"] = config.query_id_nav_1y
    if config.query_id_dividends: update_data["query_id_dividends"] = config.query_id_dividends
        
    db.system_config.update_one(
        {"_id": "ibkr_config"},
        {"$set": update_data},
        upsert=True
    )
    return {"status": "success"}

@router.post("/integrations/ibkr/test")
@log_endpoint
def test_ibkr_connection(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    config = db.system_config.find_one({"_id": "ibkr_config"})
    
    if not config or not config.get("flex_token"):
        return {"success": False, "message": "No token configured."}
        
    return {"success": True, "message": "Token found (Dry Run Verification)"}

from fastapi import BackgroundTasks
from app.services.ibkr_service import run_ibkr_sync

@router.post("/integrations/ibkr/sync")
@log_endpoint
async def sync_ibkr_data(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    stale_hours: float = 0.0,
    nav_days: int = 0
):
    """
    Trigger manual sync of IBKR Portfolio and Trades.
    stale_hours: If > 0, skips if data is fresher than this (Auto-Sync).
    nav_days: If > 0, requests specific N-day report for NAV (Live).
    """
    if current_user.role != "admin": # Or 'portfolio' role? For now Admin.
        raise HTTPException(status_code=403, detail="Not authorized")
        
    background_tasks.add_task(run_ibkr_sync, stale_hours, nav_days)
    return {"status": "queued", "message": "IBKR Sync started in background."}

@router.post("/integrations/ibkr/sync/nav-all")
@log_endpoint
async def sync_all_nav_reports(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Trigger comprehensive sync of ALL configured NAV reports (1D, 7D, 30D, MTD, etc).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    from app.services.ibkr_service import trigger_all_nav_reports
    background_tasks.add_task(trigger_all_nav_reports)
    return {"status": "queued", "message": "Full NAV Schedule triggered."}

@router.get("/portfolio/stats")
@log_endpoint
async def get_portfolio_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    account_id: str | None = None,
):
    """Get calculated NAV stats (Current, 30d, YTD, etc)."""
    # Helper to protect View
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    from app.services.portfolio_analysis import get_nav_history_stats
    return get_nav_history_stats(account_id=account_id)


@router.get("/portfolio/live-status")
@log_endpoint
async def get_portfolio_live_status(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")

    tws_service = get_ibkr_tws_service()
    return tws_service.get_live_status()


@router.get("/portfolio/nav/live")
@log_endpoint
async def get_portfolio_live_nav(
    current_user: Annotated[User, Depends(get_current_active_user)],
    account_id: str | None = None,
):
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")

    from app.services.portfolio_analysis import get_latest_live_nav_snapshot

    snapshot = get_latest_live_nav_snapshot(account_id=account_id)
    return snapshot or {
        "timestamp": None,
        "total_nav": 0,
        "unrealized_pnl": 0,
        "realized_pnl": 0,
        "accounts": [],
        "source": "tws",
        "last_tws_update": None,
    }


@router.get("/orders/open")
@log_endpoint
async def get_open_orders(
    current_user: Annotated[User, Depends(get_current_active_user)],
    active_only: bool = True,
):
    """
    Return normalized open/working orders with optional ticker market context.
    """
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")

    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")

    sources = ["tws_open_order", "flex_order_history"]
    orders = list(db.ibkr_orders.find({"source": {"$in": sources}}, {"_id": 0}))

    normalized_rows = [_normalize_order_row(order) for order in orders]
    if active_only:
        normalized_rows = [row for row in normalized_rows if row.get("is_active")]

    # Keep newest updates first by default.
    normalized_rows.sort(
        key=lambda row: (
            str(row.get("last_update") or ""),
            str(row.get("account_id") or ""),
            str(row.get("display_symbol") or ""),
        ),
        reverse=True,
    )

    market_cache: dict[str, dict] = {}
    for row in normalized_rows:
        ticker = row.get("underlying_symbol") or row.get("symbol")
        ticker = str(ticker or "").strip().upper() or None
        row["underlying_ticker"] = ticker
        if ticker not in market_cache:
            market_cache[ticker] = _market_context_for_ticker(db, ticker)
        row.update(market_cache[ticker])

    return normalized_rows


@router.get("/orders/live-status")
@log_endpoint
async def get_order_live_status(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")

    tws_service = get_ibkr_tws_service()
    return tws_service.get_live_status()

@router.get("/nav/report/{report_type}")
@log_endpoint
def get_nav_report_endpoint(
    report_type: NavReportType,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    account_id: str | None = None,
):
    """
    Get generic NAV report data.
    If data for today is missing for this specific report type, trigger async fetch.
    Returns status='fetching' (202) if triggered, or status='available' with data if present.
    """
    # 1. Check if we have stats
    from app.services.portfolio_analysis import get_report_stats
    stats_data = get_report_stats(report_type, account_id=account_id)
    
    if stats_data:
        return {
            "status": "available",
            "stats": stats_data
        }
        
    # 2. If not found, Trigger Fetch
    # Only if truly missing from DB.
    # Note: validation of "freshness" is handled by the user pressing the button again? 
    # Or should we enforce "today"?
    # The user said "simple single call". If old data is there, give it?
    # Assuming "get_report_stats" returns the LATEST available.
    if not stats_data:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        recent_entry = db.ibkr_raw_flex_reports.find_one({
            "ibkr_report_type": report_type,
            # We can check date if we want strict freshness
        })
        # If we have raw report but parsing failed? Unlikely.
        
        # Trigger background fetch if absolutely nothing found
        background_tasks.add_task(fetch_and_store_nav_report, report_type)
        return {"status": "fetching", "message": f"Report {report_type} requested."}
    
    return {"status": "error", "message": "Unknown state"}

@router.get("/portfolio/holdings")
@log_endpoint
async def get_portfolio_holdings(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get latest snapshot of holdings."""
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    data = _load_portfolio_holdings_rows(db)
    if not data:
        return []
    
    # Enrich with Dividend History
    symbols = list(set([h["symbol"] for h in data if "symbol" in h]))
    if symbols:
        pipeline = [
            {"$match": {"symbol": {"$in": symbols}, "code": "RE"}},
            {"$group": {"_id": "$symbol", "total_divs": {"$sum": "$net_amount"}}}
        ]
        div_sums = {doc["_id"]: doc["total_divs"] for doc in db.ibkr_dividends.aggregate(pipeline)}
        
        for row in data:
            sym = row.get("symbol")
            if not sym: continue
            
            divs = float(div_sums.get(sym, 0.0) or 0.0)
            row["divs_earned"] = divs
            
            unrealized = _safe_float(row.get("unrealized_pnl"))
            row["total_return"] = (unrealized if unrealized is not None else None)
            if row["total_return"] is not None:
                row["total_return"] += divs
            
            cb = _safe_float(row.get("cost_basis"))
            if cb is not None and cb > 0:
                row["true_yield"] = divs / cb
            else:
                row["true_yield"] = None

    # 3. Enhanced Metrics (Coverage, DTE, ITM/OTM)
    from app.services.options_analysis import OptionsAnalyzer
    analyzer_input = []
    for row in data:
        sanitized = dict(row)
        if sanitized.get("cost_basis") is None:
            sanitized["cost_basis"] = 0
        if sanitized.get("quantity") is None:
            sanitized["quantity"] = 0
        analyzer_input.append(sanitized)

    analyzer = OptionsAnalyzer(analyzer_input)
    grouped = analyzer.grouped
    now = datetime.now()
    coverage_by_account = defaultdict(lambda: {"shares": 0.0, "short_calls": 0.0})
    underlying_price_by_account = {}

    for row in data:
        account_id = row.get("account_id") or row.get("account") or "UNKNOWN"
        und = row.get("underlying_symbol") or row.get("underlying") or row.get("symbol")
        if not und:
            continue

        sec_type = row.get("security_type") or row.get("asset_class") or row.get("AssetClass") or row.get("secType") or row.get("sec_type")
        qty = _safe_float(row.get("quantity"))
        if qty is None:
            qty = _safe_float(row.get("position"))
        if qty is None:
            qty = 0.0
        key = (account_id, und)

        if sec_type == "STK":
            coverage_by_account[key]["shares"] += qty
            market_price = _safe_float(row.get("market_price"))
            if market_price is not None and market_price > 0:
                underlying_price_by_account[key] = market_price
        elif _is_short_call_position(row):
            multiplier = _safe_float(row.get("multiplier"))
            if multiplier is None:
                multiplier = 100.0
            coverage_by_account[key]["short_calls"] += abs(qty) * multiplier

    pending_summary_by_account = _load_pending_order_summaries(db, coverage_by_account)

    for row in data:
        # A. Coverage Status
        und = row.get("underlying_symbol") or row.get("underlying") or row.get("symbol")
        account_id = row.get("account_id") or row.get("account") or "UNKNOWN"
        account_stats = coverage_by_account.get((account_id, und), {"shares": 0.0, "short_calls": 0.0})
        # Keep the old grouped-based special case (not related to account-specific row rows)
        stats = grouped.get(und)
        if stats or und:
            shares = account_stats["shares"]
            covered = account_stats["short_calls"]
            row["coverage_group_key"] = f"{account_id}:{und}"
            row["covered_shares"] = covered
            row["share_quantity_total"] = shares
            if _is_flat_position_row(row):
                status, mismatch = "", False
            else:
                status, mismatch = _resolve_coverage_status(shares, covered)
            row["coverage_status"] = status
            row["coverage_mismatch"] = mismatch
            pending_summary = pending_summary_by_account.get((account_id, und), {})
            row["pending_order_count"] = pending_summary.get("pending_order_count", 0)
            row["pending_order_effect"] = pending_summary.get("pending_order_effect", "none")
            row["coverage_status_if_filled"] = pending_summary.get("coverage_status_if_filled", status)
            row["pending_cover_shares"] = pending_summary.get("pending_cover_shares", 0.0)
            row["pending_cover_contracts"] = pending_summary.get("pending_cover_contracts", 0.0)
            row["pending_buy_to_close_contracts"] = pending_summary.get("pending_buy_to_close_contracts", 0.0)
            row["pending_roll_contracts"] = pending_summary.get("pending_roll_contracts", 0.0)
            row["uncovered_shares_now"] = pending_summary.get("uncovered_shares_now", max(0.0, shares - covered))

        # B. Option Metrics
        sec_type = row.get("security_type") or row.get("asset_class") or row.get("AssetClass") or row.get("secType") or row.get("sec_type")
        if sec_type in ["OPT", "FOP"]:
            # Parse Expiry & DTE
            exp_str = row.get("expiry")
            if exp_str:
                try:
                    if len(exp_str) == 8 and "-" not in exp_str:
                         exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                    else:
                         exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                    
                    dte = (exp_dt.date() - now.date()).days
                    row["dte"] = dte
                    row["is_expiring_soon"] = dte <= 6
                except:
                    pass
            
            # Strike Distance & ITM
            _, _, parsed_strike = _extract_option_fields(row)
            strike = parsed_strike if parsed_strike is not None else _safe_float(row.get("strike"))
            if strike is None:
                strike = 0.0
            underlying_price = underlying_price_by_account.get((account_id, und))
            if underlying_price is None:
                underlying_price = _safe_float(row.get("underlying_price"))
            if underlying_price is None:
                underlying_price = _safe_float(row.get("underlying_last"))
            if underlying_price is None:
                underlying_price = _safe_float(row.get("underlying_market_price"))

            if strike > 0 and underlying_price is not None and underlying_price > 0:
                # Near-money / OTM distance should compare option strike to the underlying stock price,
                # not to the option premium itself. We use absolute distance so "near" works in either direction.
                row["dist_to_strike_pct"] = abs(underlying_price - strike) / underlying_price
                row["underlying_market_price"] = underlying_price
                
                # ITM Check using OSI symbol (AAPL  250117C00150000)
                # re is already imported in routes.py (line 34 in options_analysis, but I need it here)
                # But I can just check for 'C' or 'P' after the date.
                sym = row.get("local_symbol") or row.get("symbol", "")
                if re.search(r'\d{6}C\d+', sym):
                    row["is_itm"] = underlying_price >= strike
                elif re.search(r'\d{6}P\d+', sym):
                    row["is_itm"] = underlying_price <= strike
                else:
                    row["is_itm"] = False

    return data

@router.get("/portfolio/alerts")
@log_endpoint
async def get_portfolio_alerts(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Run Advanced Options Analysis on current holdings.
    Returns list of Alert objects (Uncovered, Naked, Profit).
    """
    if current_user.role not in ["admin", "portfolio"]:
        raise HTTPException(status_code=403, detail="Portfolio access required")
        
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Fetch Latest Holdings (Snapshot)
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    snapshot_id = latest.get("snapshot_id")
    if snapshot_id:
        query = {"snapshot_id": snapshot_id}
    else:
        query = {"report_date": latest.get("report_date")}
        
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    # 2. Fetch Market Data for Context
    # We want a map {Symbol: StockDataDict}
    # Optimize: Only fetch for symbols in holdings? Or just fetch all (dataset is small enough).
    stock_cursor = db.stock_data.find({}, {"_id": 0})
    market_data = {item["Ticker"]: item for item in stock_cursor}
    
    # 3. Analyze
    from app.services.options_analysis import OptionsAnalyzer
    analyzer = OptionsAnalyzer(holdings, market_data=market_data)
    
    alerts = []
    alerts.extend(analyzer.analyze_naked())    # Critical
    alerts.extend(analyzer.analyze_coverage()) # Opportunity (Filtered by Trend)
    alerts.extend(analyzer.analyze_profit())   # Actionable
    
    return alerts

class ScannerConfig(BaseModel):
    preset: str = None # "momentum", "juicy", or None for custom (future)
    criteria: dict = None
    persist: bool = False

@router.post("/analysis/scan")
@log_endpoint
def run_stock_scanner(
    config: ScannerConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Run a stock scan based on a preset or criteria.
    Presets: 'momentum', 'juicy'
    """
    from app.services.scanner_service import scan_momentum_calls, scan_juicy_candidates, run_scanner
    
    if config.preset == "momentum":
        return scan_momentum_calls(persist=config.persist)
    elif config.preset == "juicy":
        return scan_juicy_candidates(persist=config.persist)
    elif config.criteria:
        # Advanced: Pass raw criteria (Sanitize/Limit in service recommended)
        return run_scanner(config.criteria, persist=config.persist)
    else:
         raise HTTPException(status_code=400, detail="Must provide preset or criteria")


class RollInput(BaseModel):
    symbol: str
    strike: float
    expiration: str # YYYY-MM-DD
    position_type: str = "call" # call/put

@router.post("/analysis/roll")
@log_endpoint
def analyze_rolls(
    input: RollInput,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Analyze potential rolls for an options position.
    Uses real-time data from Yahoo Finance.
    """
    from app.services.roll_service import RollService
    service = RollService()
    result = service.find_rolls(
        symbol=input.symbol,
        current_strike=input.strike,
        current_exp_date=input.expiration,
        position_type=input.position_type
    )
    
    if "error" in result:
         raise HTTPException(status_code=400, detail=result["error"])
         
    return result

# --- Ticker & Opportunity Analysis ---
@router.get("/analysis/rolls")
@log_endpoint
def analyze_smart_rolls(
    current_user: Annotated[User, Depends(get_current_active_user)],
    persist: bool = False
):
    """
    Scan the USER's portfolio for Short Calls expiring soon (default 10 days)
    and find Smart Roll opportunities (Up & Out, Credit, Short Duration).
    """
    # 1. Fetch Portfolio
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Get latest holdings
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    if not holdings:
        return []
        
    # 2. Analyze
    from app.services.roll_service import RollService
    service = RollService()
    
    # Analyze
    # Analyze
    suggestions = service.analyze_portfolio_rolls(holdings, max_days_to_expiration=10, persist=persist)
    
    return suggestions


@router.get("/analysis/rolls/{ticker}")
@log_endpoint
def analyze_ticker_smart_rolls(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get Smart Roll opportunities for a specific ticker's held options.
    Flattened list for TickerModal consumption.
    """
    ticker = ticker.upper().strip()
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Get latest holdings
    latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
    if not latest:
        return []
        
    query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
    # Filter by symbol in query to save bandwidth
    query["symbol"] = ticker
    
    holdings = list(db.ibkr_holdings.find(query, {"_id": 0}))
    
    if not holdings:
        return []
        
    from app.services.roll_service import RollService
    service = RollService()
    
    # We use analyze_portfolio_rolls logic but specifically for this list
    suggestions = service.analyze_portfolio_rolls(holdings, max_days_to_expiration=45) # Allow wider window for specific analysis
    
    # Flatten: TickerModal expects a list of rolls.
    # But wait, TickerModal might expect the 'Candidate' objects directly?
    # Each suggestion in 'suggestions' has 'rolls': [Candidate, Candidate...]
    # If we return a flat list of candidates, we need to attach "Origin" info to them?
    # SmartRollView (line 382) uses {roll.strike} {roll.type}
    # Those are properties of the CANDIDATE.
    
    flattened_rolls = []
    for s in suggestions:
        candidates = s.get("rolls", [])
        for c in candidates:
            # Attach origin context if needed?
            # c["origin_strike"] = ... 
            flattened_rolls.append(c)
            
    # Sort by score across all positions?
    flattened_rolls.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return flattened_rolls


@router.get("/api/news/{symbol}")
@log_endpoint
def get_ticker_news(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 5
):
    """
    Get aggregated news with sentiment and logic analysis for a ticker.
    """
    from app.services.news_sentiment import NewsSentimentService
    service = NewsSentimentService()
    return service.get_ticker_news(symbol, limit)

# --- X-DIV & Calendar Endpoints ---

@router.get("/api/opportunities")
@log_endpoint
def get_opportunities(
    current_user: Annotated[User, Depends(get_current_active_user)],
    source: str = None,
    limit: int = 100
):
    """
    Get persisted opportunities from the database.
    """
    from app.services.opportunity_service import OpportunityService
    service = OpportunityService()
    return service.get_opportunities(source=source, limit=limit)

@router.get("/analysis/dividend-capture")
@log_endpoint
def scan_dividend_capture(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[any, Depends(get_db)],
    force_scan: bool = False
):
    logging.info(f"User {current_user.username} requested Dividend Capture Scan (force_scan={force_scan}).")
    try:
        if not force_scan:
            # Return persisted results
            from app.services.opportunity_service import OpportunityService
            service = OpportunityService()
            results = service.get_opportunities(source="DividendScanner", limit=200)
            
            # Dedupe: Keep latest per symbol
            # Assuming results are sorted by created_at desc (or natural insertion order desc)
            # We use a dict to keep the first occurrence (latest)
            unique_results = {}
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            for r in results:
                proposal = r.get("proposal", {})
                sym = proposal.get("symbol")
                ex_date = proposal.get("ex_date")
                
                # Filter out past ex-dividend dates
                if ex_date and ex_date < today_str:
                    continue
                    
                if sym and sym not in unique_results:
                     unique_results[sym] = proposal
            
            return list(unique_results.values())

        # 1. Get Tickers from Portfolio and Tracked Stocks
        # db is already connected via dependency
        
        symbols_set = set()
        
        # Get symbols from latest portfolio holdings
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        if latest:
            query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
            holdings = list(db.ibkr_holdings.find(query, {"symbol": 1}))
            symbols_set.update([h["symbol"] for h in holdings if h.get("symbol")])
            logging.info(f"Adding portfolio symbols. Current count: {len(symbols_set)}")
        else:
            logging.warning("No portfolio holdings found.")
            
        # Get all tracked tickers from stock_data
        try:
            tracked_tickers = db.stock_data.distinct("Ticker")
            if tracked_tickers:
                symbols_set.update(tracked_tickers)
                logging.info(f"Adding tracked symbols. Total distinct count: {len(symbols_set)}")
        except Exception as e:
            logging.warning(f"Could not fetch tracked tickers: {e}")
            
        symbols = list(symbols_set)
        
        if not symbols:
            return []
            
        from app.services.dividend_scanner import DividendScanner
        scanner = DividendScanner()
        results = scanner.scan_dividend_capture_opportunities(symbols)
        logging.info(f"Scan complete. Found {len(results)} opportunities.")
        return results
    except Exception as e:
        logging.error(f"Error in scan_dividend_capture: {e}", exc_info=True)
        # Raise generic 500
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/dividend-capture/{ticker}")
@log_endpoint
def get_dividend_capture_analysis(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get detailed Buy-Write analysis for a ticker.
    """
    try:
        from app.services.dividend_scanner import DividendScanner
        scanner = DividendScanner()
        strategies = scanner.analyze_capture_strategy(ticker)
        return strategies
    except Exception as e:
        logging.error(f"Error getting analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/dividends.ics")
@log_endpoint
def get_dividend_calendar():
    """
    Generate an ICS calendar file (or text fallback) with upcoming Corporate Events (Ex-Div, Earnings).
    Persists daily files to 'xdivs/' directory to avoid re-fetching.
    """
    import yfinance as yf
    from fastapi.responses import Response, FileResponse
    import os

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cache_dir = "xdivs"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        
    filename = f"corporate_events_{today_str}.ics"
    file_path = os.path.join(cache_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/calendar", filename="corporate_events.ics")

    # 2. Generate if missing
    from app.services.dividend_scanner import DividendScanner
    scanner = DividendScanner()
    try:
        generated_path = scanner.generate_corporate_events_calendar()
        return FileResponse(generated_path, media_type="text/calendar", filename="corporate_events.ics")
    except Exception as e:
        # Fallback empty response or error
        return Response(content=f"Error generating calendar: {str(e)}", status_code=500)


@router.get("/calendar/juicy.ics")
@log_endpoint
def get_juicy_calendar():
    """
    Stable ICS subscription endpoint alias for calendar clients.
    Returns the same combined corporate-events feed as /calendar/dividends.ics.
    """
    return get_dividend_calendar()

@router.get("/api/macro")
@log_endpoint
def get_macro_summary(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get key macro economic indicators.
    """
    from app.services.macro_service import MacroService
    service = MacroService()
    return service.get_macro_summary()


@router.get("/analysis/signals/{ticker}")
@log_endpoint
def get_ticker_signals(
    ticker: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get experimental Kalman Filter and Markov Chain signals for a ticker.
    (Requires daily data history).
    """
    
    ticker = _normalize_ticker_symbol(ticker)
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    stock, _, ticker = _find_stock_data_by_symbol(db, ticker)

    # DB-first preferred path: return persisted signal payload if present.
    if stock and isinstance(stock.get("signals"), dict):
        signals_payload = stock.get("signals") or {}
        freshness = _evaluate_stock_data_freshness(stock, tier="mixed")
        _queue_stock_refresh_if_stale(background_tasks, ticker, freshness)
        return {
            "ticker": ticker,
            "kalman": signals_payload.get("kalman", {}),
            "markov": signals_payload.get("markov", {}),
            "advice": signals_payload.get("advice", {}),
            **freshness,
        }

    # Fallback path: compute from external history.
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        service = SignalService()
        
        kalman = service.get_kalman_signal(data)
        markov = service.get_markov_probabilities(data)
        advice = service.get_roll_vs_hold_advice(ticker, {}, mock_price_data=data)
        _persist_signal_payload(db, ticker, kalman, markov, advice)
        
        freshness = _evaluate_stock_data_freshness(stock, tier="mixed")
        if stock:
            _queue_stock_refresh_if_stale(background_tasks, ticker, freshness)
        else:
            freshness["data_source"] = "yfinance_live"
            freshness["is_stale"] = True
            freshness["stale_reason"] = "db_record_missing"
            freshness["refresh_queued"] = False

        return {
            "ticker": ticker,
            "kalman": kalman,
            "markov": markov,
            "advice": advice,
            **freshness,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
    # Define key indicators to fetch
    indicators = [
        {"id": "FEDFUNDS", "title": "Fed Funds Rate"},
        {"id": "CPIAUCSL", "title": "CPI Inflation"},
        {"id": "UNRATE", "title": "Unemployment Rate"}
    ]
    
    results = []
    for ind in indicators:
        val = service.fetch_indicator(ind["id"], ind["title"])
        if val:
            results.append(val)
            
    return {
        "market_regime": service.get_market_condition(),
        "indicators": results
    }

@router.get("/ticker/{symbol}")
@log_endpoint
def get_ticker_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get detailed analytics for a single ticker.
    Includes: Current Price, Stats, and basic metadata.
    """
    symbol = _normalize_ticker_symbol(symbol)
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # Fetch from stock_data
    stock, stock_query, symbol = _find_stock_data_by_symbol(db, symbol)
    if not stock:
        # transform default structure if not found
        freshness = _evaluate_stock_data_freshness(None, tier="mixed")
        return {"symbol": symbol, "found": False, "price": 0.0, **freshness}

    # DB-first path: do not block modal rendering on live yfinance calls.
    company_name = stock.get("Company Name") or symbol

    profile = stock.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    if "news" not in profile:
        profile["news"] = []

    freshness = _evaluate_stock_data_freshness(stock, tier="mixed")
    _queue_stock_refresh_if_stale(background_tasks, symbol, freshness)

    return {
        "symbol": symbol,
        "found": True,
        "data": stock,
        "company_name": company_name,
        "profile": profile,
        **freshness,
    }

@router.get("/opportunity/{symbol}")
@log_endpoint
def get_opportunity_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get 'Juicy' opportunity analysis for a ticker.
    """
    symbol = _normalize_ticker_symbol(symbol)
    # reuse scanner service logic or just return raw data meant for opportunity view
    from app.services.scanner_service import scan_juicy_candidates
    
    # We might want to see if THIS specific symbol is juicy.
    # For now, let's fetch the stock data and run a quick check?
    # Or just return the pre-calculated metrics from the daily scan if available?
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    stock, _, symbol = _find_stock_data_by_symbol(db, symbol)
    
    if not stock: # fallback
         freshness = _evaluate_stock_data_freshness(None, tier="price")
         return {"symbol": symbol, "juicy_score": 0, "message": "Ticker not found in database", **freshness}

    # Calculate simple score on the fly (reusing logic from scanner conceptually)
    # TODO: Import a dedicated scorer
    iv_rank = stock.get("IV Rank", 0)
    liquidity = stock.get("Liquidity Rating", 0)
    
    score = 0
    reasons = []
    if iv_rank > 50: 
        score += 20
        reasons.append("High IV Rank")
    if liquidity > 3:
        score += 10
        reasons.append("High Liquidity")
        
    # --- Risk Analysis Integration ---
    from app.services.risk_service import RiskService
    risks = RiskService.analyze_risk(stock)

    freshness = _evaluate_stock_data_freshness(stock, tier="price")
    _queue_stock_refresh_if_stale(background_tasks, symbol, freshness)
    
    return {
        "symbol": symbol,
        "juicy_score": score,
        "reasons": reasons,
        "risks": risks,  # New Field
        "metrics": {
             "iv_rank": iv_rank,
             "liquidity": liquidity,
             "call_put_skew": stock.get("Call/Put Skew"),
             "rsi_14": stock.get("RSI_14"),
             "atr_14": stock.get("ATR_14"),
        },
        **freshness,
    }

@router.get("/portfolio/optimizer/{symbol}")
@log_endpoint
def get_portfolio_optimizer(
    symbol: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_meta: bool = False,
):
    """
    Get optimization suggestions for a ticker (e.g. Covered Call candidates).
    """
    symbol = _normalize_ticker_symbol(symbol)
    
    # Reuse option_optimizer.py logic if possible
    # For V1, we return a stub or simple suggestions based on price
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    stock, _, symbol = _find_stock_data_by_symbol(db, symbol)
    freshness = _evaluate_stock_data_freshness(stock, tier="price")
    
    if not stock:
        if include_meta:
            return {"symbol": symbol, "suggestions": [], **freshness}
        return []

    _queue_stock_refresh_if_stale(background_tasks, symbol, freshness)
        
    price = stock.get("Current Price", 0)
    
    # Simple heuristic suggestions
    suggestions = []
    
    # 1. Covered Call (selling OTM)
    if price > 0:
        strike_target = price * 1.05 # 5% OTM
        suggestions.append({
            "strategy": "Covered Call",
            "action": "SELL CALL",
            "strike_target": round(strike_target, 1),
            "reason": "Generate Income (5% OTM Target)"
        })
        
        # 2. Cash Secured Put (buying dip)
        strike_dip = price * 0.90 # 10% OTM
        suggestions.append({
            "strategy": "Cash Secured Put",
            "action": "SELL PUT",
            "strike_target": round(strike_dip, 1),
            "reason": "Acquire at discount (-10% Target)"
        })

    # --- Smart Roll Assistant Integration ---
    # Check if we hold options for this ticker to suggest rolls
    holdings = list(db.ibkr_holdings.find({"symbol": symbol}, {"_id": 0}))
    if holdings:
        from app.services.roll_service import RollService
        roll_service = RollService()
        
        for pos in holdings:
            # We only care about options for rolling (secType usually 'OPT')
            if pos.get("secType") == "OPT":
                # Extract details (assuming standard IBKR fields)
                # We need strike, exp, right. 
                # Our schema might vary, let's try to extract safely.
                try:
                    current_strike = float(pos.get("strike", 0))
                    exp_date = pos.get("expiry") # Format might be YYYYMMDD or YYYY-MM-DD
                    if exp_date and len(exp_date) == 8:
                        exp_date = f"{exp_date[:4]}-{exp_date[4:6]}-{exp_date[6:]}"
                    
                    right = pos.get("right") # 'C' or 'P'
                    position = float(pos.get("position", 0))
                    
                    if position != 0:
                        position_type = "call" if right == "C" else "put"
                        # Use RollService
                        rolls = roll_service.find_rolls(
                            symbol=symbol,
                            current_strike=current_strike,
                            current_exp_date=exp_date,
                            position_type=position_type
                        )
                        
                        if "rolls" in rolls:
                             # Add top 3 rolls as suggestions
                             for r in rolls["rolls"][:3]:
                                 suggestions.append({
                                     "strategy": f"Roll {position_type.title()}",
                                     "action": f"ROLL to {r['expiration']} {r['strike']} ({r['roll_type']})",
                                     "reason": f"Net Credit: ${r['net_credit']:.2f}. {r['roll_type']} roll."
                                 })
                except Exception as e:
                    # Log error but don't break generic suggestions
                    print(f"Error calculating rolls for {symbol}: {e}")
    
    if include_meta:
        return {"symbol": symbol, "suggestions": suggestions, **freshness}
    return suggestions


@router.get("/portfolio/export/csv")
@log_endpoint
def export_portfolio_csv(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Authenticated download endpoint (keeps previous behaviour).
    """
    return _get_portfolio_csv_response(username=current_user.username, origin="auth")


@router.post("/portfolio/export/url")
@log_endpoint
def create_portfolio_export_url(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Create a short-lived, one-time download URL for the authenticated user."""
    from datetime import datetime, timedelta
    from jose import jwt
    import logging

    logger = logging.getLogger(__name__)
    try:
        ttl = 60  # seconds
        payload = {
            "sub": current_user.username,
            "purpose": "download_portfolio",
            "exp": datetime.utcnow() + timedelta(seconds=ttl)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        url = f"/api/portfolio/export/csv/download?dl_token={token}"
        logger.info(f"Routes.create_portfolio_export_url - user={current_user.username} issued token, expires_in={ttl}s")
        return {"url": url, "expires_in": ttl}
    except Exception as e:
        logger.exception("Routes.create_portfolio_export_url - failed to create token")
        from fastapi.responses import Response
        import traceback
        error_msg = f"Failed to create download URL:\n{str(e)}\n\n{traceback.format_exc()}"
        return Response(content=error_msg, status_code=500, media_type="text/plain")


@router.get("/portfolio/export/csv/download")
@log_endpoint
def download_portfolio_with_token(dl_token: str):
    """Download endpoint that accepts a short-lived dl_token in querystring (no auth dependency)."""
    from jose import jwt
    import logging
    from fastapi.responses import Response

    logger = logging.getLogger(__name__)
    try:
        claims = jwt.decode(dl_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if claims.get("purpose") != "download_portfolio":
            raise Exception("Invalid token purpose")
        username = claims.get("sub")
        logger.info(f"Routes.download_portfolio_with_token - valid token for user={username}")
        return _get_portfolio_csv_response(username=username, origin="token")
    except Exception as e:
        logger.warning(f"Routes.download_portfolio_with_token - invalid/expired token: {e}")
        return Response(content="Invalid or expired download token", status_code=401, media_type="text/plain")


def _get_portfolio_csv_response(username: str, origin: str):
    """Internal helper to generate the Response for CSV data as plain text."""
    from fastapi.responses import Response
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Routes._get_portfolio_csv_response - start username={username} origin={origin}")

        from app.services.export_service import generate_portfolio_csv_content

        csv_content = generate_portfolio_csv_content()

        # Return as plain text for the frontend to handle in a new window/tab
        return Response(content=csv_content, media_type="text/plain")

    except Exception as e:
        logger.exception(f"Routes._get_portfolio_csv_response - exception for username={username}: {e}")
        error_msg = f"Export Failed:\n{str(e)}\n\n{traceback.format_exc()}"
        return Response(content=error_msg, status_code=500, media_type="text/plain")


# --- Tracked Ticker Management ---

class TickerInput(BaseModel):
    ticker: str

@router.get("/stocks/tracked", response_model=List[str])
@log_endpoint
def get_tracked_tickers(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get the list of tickers currently being tracked."""
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    doc = db.system_config.find_one({"_id": "tracked_tickers"})
    
    tracked_list = sorted(doc["tickers"]) if doc and "tickers" in doc else []
    
    # Lazy Sync: Auto-add portfolio holdings for privileged users
    if current_user.role in ["admin", "portfolio"]:
        try:
            from app.services.ticker_discovery import discover_and_track_tickers
            new_list = discover_and_track_tickers()
            
            if new_list:
                # Update return list immediately so UI sees them
                tracked_list = sorted(list(set(tracked_list).union(new_list)))
                
                # Trigger background fetch for new info
                background_tasks.add_task(
                    background_job_wrapper, 
                    f"auto_add_{len(new_list)}", 
                    lambda: run_stock_live_comparison(new_list, trigger="sync")
                )
        except Exception as e:
            # Log but don't fail the request
            print(f"Error in lazy portfolio sync: {e}")

    if tracked_list:
        return tracked_list
    
    # Fallback to defaults from script if not in DB yet (will trigger migration on next run)
    from app.services.stock_live_comparison import StockLiveComparison
    return StockLiveComparison.get_default_tickers()

@router.post("/stocks/tracked")
@log_endpoint
def add_tracked_ticker(
    ticker_input: TickerInput,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Add a ticker to the tracking list and trigger an immediate fetch."""
    ticker = ticker_input.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Update List
    # Use $addToSet to avoid duplicates
    result = db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$addToSet": {"tickers": ticker}},
        upsert=True
    )
    
    # 2. Trigger Fetch for this specific ticker
    from app.jobs import create_job
    job = create_job()
    
    # We use the existing function but pass only this ticker to limit scope
    background_tasks.add_task(
        background_job_wrapper,
        job.id,
        lambda: run_stock_live_comparison([ticker], trigger="sync"),
    )
    
    return {"status": "success", "message": f"Added {ticker} to tracking list.", "job_id": job.id}

@router.delete("/stocks/tracked/{ticker}")
@log_endpoint
def remove_tracked_ticker(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Remove a ticker from the tracking list."""
    ticker = ticker.upper().strip()
    
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Remove from List
    db.system_config.update_one(
        {"_id": "tracked_tickers"},
        {"$pull": {"tickers": ticker}}
    )
    
    # Optional: Delete the actual data record?
    # User might want to keep history, but for "Live Comparison" it might be confusing to see it if it's not "Tracked".
    # But the "Live View" comes from /stocks which dumps everything. 
    # Let's LEAVE the data for now. The user can just ignore it, or we can add a cleanup later.
    
    return {"status": "success", "message": f"Removed {ticker} from tracking list."}
