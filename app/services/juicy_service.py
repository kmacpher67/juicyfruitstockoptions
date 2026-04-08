from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import yfinance as yf


@dataclass(frozen=True)
class JuicyPreset:
    key: str
    label: str


PRESET_JUICY = JuicyPreset(key="juicy", label="Juicy Fruit Options")
PRESET_HOT_PUTS = JuicyPreset(key="hot_puts", label="Hot PUTS")


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _score_candidate(*, iv_rank: float | None, skew: float | None, tsmom_60: float | None, yield_pct: float | None, option_type: str) -> int:
    score = 0.0

    if iv_rank is not None:
        if iv_rank >= 75:
            score += 40
        elif iv_rank >= 50:
            score += 30
        elif iv_rank >= 30:
            score += 15

    if yield_pct is not None:
        if yield_pct >= 30:
            score += 25
        elif yield_pct >= 15:
            score += 18
        elif yield_pct >= 8:
            score += 10

    if skew is not None:
        if option_type == "CALL":
            if skew >= 1.2:
                score += 15
            elif skew >= 1.0:
                score += 8
        else:
            if skew <= 0.9:
                score += 15
            elif skew <= 1.0:
                score += 8

    if tsmom_60 is not None:
        if option_type == "CALL":
            score += 12 if tsmom_60 >= 0 else 4
        else:
            score += 12 if tsmom_60 < 0 else 4

    return int(max(0, min(100, round(score))))


def _liquidity_grade(volume: int, open_interest: int, spread_pct_mid: float | None) -> str:
    spread = spread_pct_mid if spread_pct_mid is not None else 9.99
    if volume >= 500 and open_interest >= 1000 and spread <= 0.03:
        return "A"
    if volume >= 100 and open_interest >= 250 and spread <= 0.08:
        return "B"
    if volume >= 10 and open_interest >= 50 and spread <= 0.20:
        return "C"
    return "D"


def _liquidity_score(grade: str) -> int:
    return {
        "A": 30,
        "B": 22,
        "C": 12,
        "D": 4,
    }.get(grade, 4)


def _timeframe_bucket(dte: int) -> str:
    if dte <= 7:
        return "daily"
    if dte <= 35:
        return "weekly"
    return "monthly"


def _short_dte_score(dte: int) -> int:
    if dte <= 7:
        return 20
    if dte <= 14:
        return 14
    if dte <= 30:
        return 8
    return 3


def _yield_score(annualized_yield_pct: float) -> int:
    if annualized_yield_pct >= 120:
        return 45
    if annualized_yield_pct >= 80:
        return 38
    if annualized_yield_pct >= 50:
        return 30
    if annualized_yield_pct >= 25:
        return 22
    if annualized_yield_pct >= 12:
        return 14
    return 6


def _chain_score(*, annualized_yield_pct: float, dte: int, liquidity_grade: str, spread_pct_mid: float | None) -> int:
    score = _yield_score(annualized_yield_pct)
    score += _short_dte_score(dte)
    score += _liquidity_score(liquidity_grade)

    if spread_pct_mid is not None:
        if spread_pct_mid > 0.20:
            score -= 20
        elif spread_pct_mid > 0.10:
            score -= 10

    return int(max(0, min(100, round(score))))


def _reason_summary(strategy: str, yield_pct: float | None, iv_rank: float | None, tsmom_60: float | None) -> str:
    parts: list[str] = [strategy]
    if yield_pct is not None:
        parts.append(f"yield {yield_pct:.1f}%")
    if iv_rank is not None:
        parts.append(f"IV {iv_rank:.0f}")
    if tsmom_60 is not None:
        parts.append(f"TSMOM {tsmom_60:+.2f}")
    return " | ".join(parts)


def _calc_dte_from_expiry(expiry_iso: Any) -> int | None:
    dt = _parse_datetime(expiry_iso)
    if not dt:
        return None
    delta = dt.date() - datetime.now(timezone.utc).date()
    return max(0, delta.days)


def _premium_from_row(bid: float, ask: float, last: float) -> float:
    if bid > 0:
        return bid
    if ask > 0 and bid > 0:
        return (ask + bid) / 2.0
    if last > 0:
        return last
    if ask > 0:
        return ask
    return 0.0


def build_chain_level_call_candidates(symbol: str, current_price: float, max_dtes: int = 4) -> list[dict]:
    if not symbol or current_price <= 0:
        return []

    ticker = yf.Ticker(symbol)
    expiries = list(ticker.options or [])[: max(1, int(max_dtes))]
    if not expiries:
        return []

    now = datetime.now(timezone.utc)
    out: list[dict] = []

    for expiry in expiries:
        try:
            chain = ticker.option_chain(expiry)
            calls = chain.calls
        except Exception:
            continue

        if calls is None or calls.empty:
            continue

        calls = calls.sort_values("strike")
        itm = calls[calls["strike"] <= current_price].tail(1)
        otm = calls[calls["strike"] > current_price].head(4)

        picks = []
        if not itm.empty:
            picks.append(("ITM", itm.iloc[0]))
        for _, row in otm.iterrows():
            picks.append(("OTM", row))

        dte = max(1, (datetime.fromisoformat(expiry).date() - now.date()).days)
        timeframe_bucket = _timeframe_bucket(dte)

        for moneyness_label, row in picks:
            strike = _safe_float(row.get("strike"))
            if strike is None:
                continue

            bid = _safe_float(row.get("bid")) or 0.0
            ask = _safe_float(row.get("ask")) or 0.0
            last = _safe_float(row.get("lastPrice")) or 0.0
            premium = _premium_from_row(bid, ask, last)

            yield_pct = (premium / current_price) * 100.0 if current_price > 0 else 0.0
            annualized_yield_pct = yield_pct * (365.0 / dte)
            spread = (ask - bid) if (ask > 0 and bid > 0) else None
            mid = ((ask + bid) / 2.0) if (ask > 0 and bid > 0) else None
            spread_pct_mid = (spread / mid) if (spread is not None and mid and mid > 0) else None

            volume = _safe_int(row.get("volume"))
            open_interest = _safe_int(row.get("openInterest"))
            liquidity_grade = _liquidity_grade(volume, open_interest, spread_pct_mid)
            score = _chain_score(
                annualized_yield_pct=annualized_yield_pct,
                dte=dte,
                liquidity_grade=liquidity_grade,
                spread_pct_mid=spread_pct_mid,
            )

            strike_distance_pct = ((strike / current_price) - 1.0) * 100.0
            strategy = f"Call {moneyness_label} {expiry}"

            out.append(
                {
                    "symbol": symbol,
                    "as_of": _iso_utc(now),
                    "strategy": strategy,
                    "type": "CALL",
                    "action": "SELL",
                    "dte": dte,
                    "strike": round(strike, 2),
                    "premium": round(premium, 4),
                    "yield_pct": round(yield_pct, 4),
                    "annualized_yield_pct": round(annualized_yield_pct, 2),
                    "score": score,
                    "reason_summary": f"{timeframe_bucket} | liq {liquidity_grade} | ann {annualized_yield_pct:.1f}%",
                    "reason": f"{moneyness_label} call sell | {timeframe_bucket} | liq {liquidity_grade}",
                    "strike_target": round(strike, 2),
                    "timeframe_bucket": timeframe_bucket,
                    "moneyness_label": moneyness_label,
                    "strike_distance_pct": round(strike_distance_pct, 3),
                    "volume": volume,
                    "open_interest": open_interest,
                    "bid": round(bid, 4),
                    "ask": round(ask, 4),
                    "bid_ask_spread": round(spread, 4) if spread is not None else None,
                    "spread_pct_mid": round(spread_pct_mid, 4) if spread_pct_mid is not None else None,
                    "liquidity_grade": liquidity_grade,
                    "preset_tags": [PRESET_JUICY.key],
                    "scoring_inputs": {
                        "annualized_yield_pct": round(annualized_yield_pct, 2),
                        "yield_pct": round(yield_pct, 4),
                        "dte": dte,
                        "volume": volume,
                        "open_interest": open_interest,
                        "spread_pct_mid": round(spread_pct_mid, 4) if spread_pct_mid is not None else None,
                        "liquidity_grade": liquidity_grade,
                        "timeframe_bucket": timeframe_bucket,
                    },
                    "data_source": "yfinance_chain",
                }
            )

    out.sort(key=lambda row: (row.get("score") or 0), reverse=True)
    return out


def build_juicy_candidates(stock: dict, symbol: str, include_chain_rows: bool = True) -> list[dict]:
    now = datetime.now(timezone.utc)
    as_of_dt = _parse_datetime(stock.get("_last_persisted_at") or stock.get("Last Update")) or now

    price = _safe_float(stock.get("Current Price"))
    if not price or price <= 0:
        return []

    iv_rank = _safe_float(stock.get("IV Rank"))
    skew = _safe_float(stock.get("Call/Put Skew"))
    tsmom_60 = _safe_float(stock.get("TSMOM_60"))

    call_yield = _safe_float(stock.get("Annual Yield Call Prem"))
    put_yield = _safe_float(stock.get("Annual Yield Put Prem"))

    call_strike = _safe_float(stock.get("1-yr 6% OTM CALL Strike") or stock.get("1Y6_OTM_CALL_STRIKE") or stock.get("6-mo Call Strike"))
    put_strike = _safe_float(stock.get("1-yr 6% OTM PUT Strike") or stock.get("1Y6_OTM_PUT_STRIKE"))
    call_premium = _safe_float(stock.get("1-yr 6% OTM CALL Price") or stock.get("1Y6_OTM_CALL_PREMIUM"))
    put_premium = _safe_float(stock.get("1-yr 6% OTM PUT Price") or stock.get("1Y6_OTM_PUT_PREMIUM"))

    call_dte = _calc_dte_from_expiry(stock.get("_CallExpDate_90") or stock.get("_CallExpDate_180") or stock.get("_CallExpDate_365"))
    put_dte = _calc_dte_from_expiry(stock.get("_PutExpDate_365"))

    candidates: list[dict] = []

    if include_chain_rows:
        try:
            candidates.extend(build_chain_level_call_candidates(symbol, price, max_dtes=4))
        except Exception:
            pass

    call_score = _score_candidate(
        iv_rank=iv_rank,
        skew=skew,
        tsmom_60=tsmom_60,
        yield_pct=call_yield,
        option_type="CALL",
    )
    candidates.append(
        {
            "symbol": symbol,
            "as_of": _iso_utc(as_of_dt),
            "strategy": "Covered Call",
            "type": "CALL",
            "action": "SELL",
            "dte": call_dte if call_dte is not None else 30,
            "strike": call_strike if call_strike is not None else round(price * 1.05, 2),
            "premium": call_premium,
            "yield_pct": call_yield,
            "annualized_yield_pct": None,
            "score": call_score,
            "reason_summary": _reason_summary("Covered Call", call_yield, iv_rank, tsmom_60),
            "reason": _reason_summary("Covered Call", call_yield, iv_rank, tsmom_60),
            "strike_target": call_strike if call_strike is not None else round(price * 1.05, 2),
            "timeframe_bucket": "monthly",
            "liquidity_grade": None,
            "volume": None,
            "open_interest": None,
            "bid_ask_spread": None,
            "spread_pct_mid": None,
            "preset_tags": [PRESET_JUICY.key],
            "scoring_inputs": {
                "iv_rank": iv_rank,
                "call_put_skew": skew,
                "tsmom_60": tsmom_60,
                "yield_pct": call_yield,
                "current_price": price,
            },
            "data_source": str(stock.get("source") or "stock_data_db"),
        }
    )

    put_score = _score_candidate(
        iv_rank=iv_rank,
        skew=skew,
        tsmom_60=tsmom_60,
        yield_pct=put_yield,
        option_type="PUT",
    )
    put_tags = [PRESET_JUICY.key]
    if tsmom_60 is not None and tsmom_60 < 0:
        put_tags.append(PRESET_HOT_PUTS.key)

    candidates.append(
        {
            "symbol": symbol,
            "as_of": _iso_utc(as_of_dt),
            "strategy": "Cash Secured Put",
            "type": "PUT",
            "action": "SELL",
            "dte": put_dte if put_dte is not None else 30,
            "strike": put_strike if put_strike is not None else round(price * 0.9, 2),
            "premium": put_premium,
            "yield_pct": put_yield,
            "annualized_yield_pct": None,
            "score": put_score,
            "reason_summary": _reason_summary("Cash Secured Put", put_yield, iv_rank, tsmom_60),
            "reason": _reason_summary("Cash Secured Put", put_yield, iv_rank, tsmom_60),
            "strike_target": put_strike if put_strike is not None else round(price * 0.9, 2),
            "timeframe_bucket": "monthly",
            "liquidity_grade": None,
            "volume": None,
            "open_interest": None,
            "bid_ask_spread": None,
            "spread_pct_mid": None,
            "preset_tags": put_tags,
            "scoring_inputs": {
                "iv_rank": iv_rank,
                "call_put_skew": skew,
                "tsmom_60": tsmom_60,
                "yield_pct": put_yield,
                "current_price": price,
            },
            "data_source": str(stock.get("source") or "stock_data_db"),
        }
    )

    hold_score = int(max(0, min(100, round((put_score + call_score) / 2.0))))
    candidates.append(
        {
            "symbol": symbol,
            "as_of": _iso_utc(as_of_dt),
            "strategy": "Hold / Wait",
            "type": "CALL" if (tsmom_60 or 0) >= 0 else "PUT",
            "action": "HOLD",
            "dte": 0,
            "strike": None,
            "premium": None,
            "yield_pct": None,
            "annualized_yield_pct": None,
            "score": hold_score,
            "reason_summary": _reason_summary("Hold / Wait", None, iv_rank, tsmom_60),
            "reason": _reason_summary("Hold / Wait", None, iv_rank, tsmom_60),
            "strike_target": None,
            "timeframe_bucket": "daily",
            "liquidity_grade": None,
            "volume": None,
            "open_interest": None,
            "bid_ask_spread": None,
            "spread_pct_mid": None,
            "preset_tags": [PRESET_JUICY.key],
            "scoring_inputs": {
                "iv_rank": iv_rank,
                "call_put_skew": skew,
                "tsmom_60": tsmom_60,
                "yield_pct": None,
                "current_price": price,
            },
            "data_source": str(stock.get("source") or "stock_data_db"),
        }
    )

    candidates.sort(key=lambda row: (row.get("score") or 0), reverse=True)
    return candidates


def _strategy_key(row: dict) -> str:
    parts = [
        str(row.get("symbol") or "").upper().strip(),
        str(row.get("strategy") or "").strip(),
        str(row.get("type") or "").strip(),
        str(row.get("action") or "").strip(),
        str(row.get("dte") if row.get("dte") is not None else ""),
        str(row.get("strike") if row.get("strike") is not None else ""),
    ]
    return "|".join(parts)


def upsert_juicy_candidates(db, symbol: str, rows: list[dict], source: str = "optimizer_api") -> list[dict]:
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    coll = db.juicy_opportunities

    for row in rows:
        strategy_key = _strategy_key(row)
        existing = coll.find_one({"strategy_key": strategy_key}, {"_id": 0, "create_date": 1}) or {}
        create_date = existing.get("create_date") or _iso_utc(now)

        doc = {
            **row,
            "strategy_key": strategy_key,
            "symbol": symbol,
            "last_updated": _iso_utc(now),
            "source": source,
        }

        coll.update_one(
            {"strategy_key": strategy_key},
            {
                "$set": doc,
                "$setOnInsert": {"create_date": create_date},
            },
            upsert=True,
        )
        out.append({**doc, "create_date": create_date})

    return sorted(out, key=lambda d: (d.get("score") or 0), reverse=True)


def get_juicy_rows(db, *, symbol: str | None = None, preset: str | None = None, limit: int = 20, sort_by: str = "score", sort_dir: str = "desc") -> list[dict]:
    query: dict[str, Any] = {}
    if symbol:
        query["symbol"] = symbol
    if preset:
        query["preset_tags"] = preset

    direction = -1 if str(sort_dir).lower() != "asc" else 1
    cursor = db.juicy_opportunities.find(query, {"_id": 0}).sort(sort_by, direction).limit(max(1, min(limit, 500)))
    return list(cursor)


def evaluate_juicy_staleness(*, now_utc: datetime, market_open: bool, juicy_last_updated: datetime | None, market_close_utc: datetime | None) -> tuple[bool, str | None]:
    if juicy_last_updated is None:
        return True, "missing_last_updated"

    if market_open:
        if (now_utc - juicy_last_updated) > timedelta(minutes=30):
            return True, "older_than_30m_during_session"
        return False, None

    if market_close_utc and juicy_last_updated < market_close_utc:
        return True, "older_than_latest_market_close"

    return False, None


def compute_latest_market_close_utc(now_utc: datetime, ny_tz, is_market_holiday_fn, is_early_close_fn) -> datetime | None:
    now_et = now_utc.astimezone(ny_tz)
    day = now_et.date()

    for _ in range(7):
        if day.weekday() < 5 and not is_market_holiday_fn(day.year, day):
            close_hour = 13 if is_early_close_fn(day.year, day) else 16
            close_et = datetime(day.year, day.month, day.day, close_hour, 0, tzinfo=ny_tz)
            close_utc = close_et.astimezone(timezone.utc)
            if close_utc <= now_utc:
                return close_utc
        day = day - timedelta(days=1)

    return None
