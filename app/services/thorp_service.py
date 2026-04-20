from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models.thorp import ThorpAuditResponse, ThorpDecision, ThorpPoint, ThorpStatus

logger = logging.getLogger(__name__)

_INSUFFICIENT = ThorpStatus.INSUFFICIENT_DATA
_EDGE = ThorpStatus.EDGE
_CAUTION = ThorpStatus.CAUTION
_RISK = ThorpStatus.RISK
_PENDING = ThorpStatus.PENDING_DATA

_CACHE_TTL_SECONDS = 1800  # 30 minutes


class ThorpService:
    """Compute the Edward Thorp 10-point per-ticker risk/edge audit."""

    def __init__(self, db: Any) -> None:
        self._db = db

    async def compute(self, symbol: str) -> ThorpAuditResponse:
        logger.info(
            "thorp_service-ThorpService-compute - INFO - starting audit symbol=%s",
            symbol,
        )

        cached = self._load_cache(symbol)
        if cached is not None:
            logger.info(
                "thorp_service-ThorpService-compute - INFO - returning cached audit symbol=%s",
                symbol,
            )
            return cached

        stock_data = self._get_stock_data(symbol)
        opp = self._get_opportunity(symbol)
        holdings = self._get_holdings(symbol)
        trades = self._get_trades(symbol)
        config = self._get_system_config()
        nlv = self._get_total_nlv()

        inflation_baseline = float(config.get("thorp_inflation_baseline", 5.9)) / 100.0
        risk_free = float(config.get("risk_free_rate", 5.3)) / 100.0

        p1 = self._edge_audit(trades, inflation_baseline)
        p2 = self._kelly_sizing(trades, opp, holdings, nlv, risk_free)
        p3 = self._inefficiency_map(stock_data)
        p4 = self._ruin_check(holdings, nlv)
        p5 = self._fraud_scan(opp, stock_data)
        p6 = self._compounding_review(trades, opp, inflation_baseline)
        p7 = self._adaptability_check(trades, symbol)
        p8 = self._independence_test(stock_data)
        p9 = self._circle_of_competence(trades)
        p10_points = [p1, p2, p3, p4, p5, p6, p7, p8, p9]
        decision = self._thorp_decision(p10_points)

        data_pts = [p1, p2, p3, p4, p5, p6, p7, p8, p9]
        sufficient = sum(
            1
            for p in data_pts
            if p.status not in (_INSUFFICIENT, _PENDING)
        )
        completeness = round(sufficient / len(data_pts), 2)

        points_with_decision = data_pts + [
            ThorpPoint(
                id="thorp_decision",
                label="Thorp Decision",
                status=_EDGE if completeness >= 0.5 else _INSUFFICIENT,
                key_metric=f"{len(decision)} actions generated",
                detail="Weighted aggregate of all 9 points. See Decision panel.",
            )
        ]

        response = ThorpAuditResponse(
            symbol=symbol,
            as_of=datetime.now(tz=timezone.utc),
            points=points_with_decision,
            thorp_decision=decision,
            data_completeness=completeness,
        )

        self._save_cache(symbol, response)
        logger.info(
            "thorp_service-ThorpService-compute - INFO - audit complete symbol=%s completeness=%.2f",
            symbol,
            completeness,
        )
        return response

    # ------------------------------------------------------------------
    # Data fetchers
    # ------------------------------------------------------------------

    def _get_stock_data(self, symbol: str) -> Dict:
        doc = self._db.stock_data.find_one(
            {"$or": [{"Symbol": symbol}, {"symbol": symbol}]},
            {"_id": 0},
        )
        return doc or {}

    def _get_opportunity(self, symbol: str) -> Dict:
        doc = self._db.juicy_opportunities.find_one(
            {"symbol": symbol},
            sort=[("timestamp", -1)],
            projection={"_id": 0},
        )
        return doc or {}

    def _get_holdings(self, symbol: str) -> Dict:
        doc = self._db.ibkr_holdings.find_one(
            {"$or": [{"symbol": symbol}, {"Symbol": symbol}]},
            {"_id": 0},
        )
        return doc or {}

    def _get_trades(self, symbol: str) -> List[Dict]:
        cursor = self._db.trades.find(
            {"$or": [{"symbol": symbol}, {"Symbol": symbol}]},
            {"_id": 0},
            sort=[("close_date", -1)],
        )
        return list(cursor)

    def _get_system_config(self) -> Dict:
        doc = self._db.system_config.find_one({}, {"_id": 0})
        return doc or {}

    def _get_total_nlv(self) -> Optional[float]:
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$market_value"}}},
        ]
        result = list(self._db.ibkr_holdings.aggregate(pipeline))
        if result:
            return float(result[0].get("total", 0) or 0)
        return None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cache(self, symbol: str) -> Optional[ThorpAuditResponse]:
        stock = self._db.stock_data.find_one(
            {"$or": [{"Symbol": symbol}, {"symbol": symbol}]},
            {"thorp_audit": 1, "_id": 0},
        )
        if not stock:
            return None
        audit = stock.get("thorp_audit")
        if not audit:
            return None
        cached_at = audit.get("cached_at")
        if not cached_at:
            return None
        if isinstance(cached_at, str):
            try:
                cached_at = datetime.fromisoformat(cached_at)
            except ValueError:
                return None
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(tz=timezone.utc) - cached_at).total_seconds()
        if age > _CACHE_TTL_SECONDS:
            return None
        try:
            return ThorpAuditResponse(**audit["payload"])
        except Exception:
            return None

    def _save_cache(self, symbol: str, response: ThorpAuditResponse) -> None:
        try:
            self._db.stock_data.update_one(
                {"$or": [{"Symbol": symbol}, {"symbol": symbol}]},
                {
                    "$set": {
                        "thorp_audit": {
                            "cached_at": datetime.now(tz=timezone.utc).isoformat(),
                            "payload": response.model_dump(),
                        }
                    }
                },
                upsert=False,
            )
        except Exception as exc:
            logger.warning(
                "thorp_service-ThorpService-_save_cache - WARNING - cache write failed symbol=%s err=%s",
                symbol,
                exc,
            )

    # ------------------------------------------------------------------
    # Point 1: Edge Audit
    # ------------------------------------------------------------------

    def _edge_audit(self, trades: List[Dict], baseline: float) -> ThorpPoint:
        logger.debug(
            "thorp_service-ThorpService-_edge_audit - DEBUG - trade_count=%d",
            len(trades),
        )
        closed = [t for t in trades if _trade_is_closed(t)]
        if len(closed) < 3:
            return ThorpPoint(
                id="edge_audit",
                label="Edge Audit",
                status=_INSUFFICIENT,
                key_metric="<3 closed trades",
                detail="Need at least 3 closed trades to compute edge.",
            )

        wins = [t for t in closed if _trade_pnl(t) > 0]
        losses = [t for t in closed if _trade_pnl(t) <= 0]
        win_rate = len(wins) / len(closed)

        avg_yield = (
            sum(_trade_yield_pct(t) for t in wins) / len(wins) / 100.0
            if wins
            else 0.0
        )
        avg_loss = (
            abs(sum(_trade_yield_pct(t) for t in losses) / len(losses)) / 100.0
            if losses
            else 0.0
        )

        edge = win_rate * avg_yield - (1.0 - win_rate) * avg_loss

        if edge > baseline:
            status = _EDGE
        elif edge > 0:
            status = _CAUTION
        else:
            status = _RISK

        return ThorpPoint(
            id="edge_audit",
            label="Edge Audit",
            status=status,
            key_metric=f"E={edge*100:.1f}% vs {baseline*100:.1f}% baseline (n={len(closed)})",
            detail=(
                f"Win rate {win_rate*100:.0f}% | avg yield {avg_yield*100:.1f}% | "
                f"avg loss {avg_loss*100:.1f}%"
            ),
        )

    # ------------------------------------------------------------------
    # Point 2: Kelly Position Sizing
    # ------------------------------------------------------------------

    def _kelly_sizing(
        self,
        trades: List[Dict],
        opp: Dict,
        holdings: Dict,
        nlv: Optional[float],
        risk_free: float,
    ) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_kelly_sizing - DEBUG - start")

        closed = [t for t in trades if _trade_is_closed(t)]
        if len(closed) < 3 or nlv is None or nlv <= 0:
            return ThorpPoint(
                id="position_sizing",
                label="Kelly Position Sizing",
                status=_INSUFFICIENT,
                key_metric="N/A",
                detail="Need >=3 closed trades and NLV to compute Kelly fraction.",
            )

        wins = [t for t in closed if _trade_pnl(t) > 0]
        losses = [t for t in closed if _trade_pnl(t) <= 0]
        win_rate = len(wins) / len(closed)

        avg_yield_pct = (
            sum(_trade_yield_pct(t) for t in wins) / len(wins) if wins else 0.0
        )
        avg_loss_pct = (
            abs(sum(_trade_yield_pct(t) for t in losses) / len(losses))
            if losses
            else 1.0
        )
        avg_loss_pct = max(avg_loss_pct, 0.01)

        b = (avg_yield_pct / 100.0) / (avg_loss_pct / 100.0)
        p = win_rate
        q = 1.0 - p

        if b <= 0:
            return ThorpPoint(
                id="position_sizing",
                label="Kelly Position Sizing",
                status=_RISK,
                key_metric="b<=0 negative odds",
                detail="Average yield ratio implies no positive edge for sizing.",
            )

        f_star = (b * p - q) / b
        half_kelly = max(f_star / 2.0, 0.0)

        position_value = float(holdings.get("market_value") or 0)
        current_pct = (position_value / nlv) * 100.0 if nlv > 0 else 0.0
        recommended_pct = half_kelly * 100.0

        if current_pct > recommended_pct * 1.25:
            status = _CAUTION
            detail = (
                f"Over-committed: {current_pct:.1f}% NLV vs Half-Kelly "
                f"{recommended_pct:.1f}% — consider reducing 1 contract."
            )
        elif f_star <= 0:
            status = _RISK
            detail = "Negative Kelly — trade has no mathematical edge at current sizing."
        else:
            status = _EDGE
            detail = (
                f"Current {current_pct:.1f}% NLV within Half-Kelly "
                f"{recommended_pct:.1f}% target."
            )

        return ThorpPoint(
            id="position_sizing",
            label="Kelly Position Sizing",
            status=status,
            key_metric=f"Half-Kelly={recommended_pct:.1f}% NLV (f*={f_star*100:.1f}%)",
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Point 3: Inefficiency Map
    # ------------------------------------------------------------------

    def _inefficiency_map(self, stock_data: Dict) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_inefficiency_map - DEBUG - start")

        skew = _safe_float(stock_data.get("call_put_skew"))
        iv_rv = _safe_float(stock_data.get("iv_vs_rv"))

        if skew is None and iv_rv is None:
            return ThorpPoint(
                id="inefficiency_map",
                label="Inefficiency Map",
                status=_INSUFFICIENT,
                key_metric="No skew/IV data",
                detail="call_put_skew and iv_vs_rv not in stock_data.",
            )

        flags: List[str] = []
        status = _EDGE

        if skew is not None:
            if skew > 1.5:
                flags.append(f"skew {skew:.2f} >1.5 (put premium elevated)")
                status = _CAUTION
            else:
                flags.append(f"skew {skew:.2f} normal")

        if iv_rv is not None:
            gap_pct = (iv_rv - 1.0) * 100.0
            if abs(gap_pct) > 20.0:
                flags.append(f"IV/RV gap {gap_pct:+.1f}% >20% (seller's edge)")
                if status != _CAUTION:
                    status = _CAUTION
            else:
                flags.append(f"IV/RV gap {gap_pct:+.1f}%")
        else:
            flags.append("IV/RV: PENDING_DATA (realized vol not computed)")
            if status == _EDGE:
                status = _PENDING

        return ThorpPoint(
            id="inefficiency_map",
            label="Inefficiency Map",
            status=status,
            key_metric=f"skew={skew if skew is not None else 'N/A'} IV/RV={'%.2f'%iv_rv if iv_rv else 'N/A'}",
            detail=" | ".join(flags),
        )

    # ------------------------------------------------------------------
    # Point 4: Ruin Check
    # ------------------------------------------------------------------

    def _ruin_check(self, holdings: Dict, nlv: Optional[float]) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_ruin_check - DEBUG - start")

        if not holdings or nlv is None or nlv <= 0:
            return ThorpPoint(
                id="ruin_check",
                label="Ruin Check (-25% Sim)",
                status=_INSUFFICIENT,
                key_metric="No position data",
                detail="ibkr_holdings missing or NLV unavailable.",
            )

        market_value = _safe_float(holdings.get("market_value"))
        if market_value is None:
            return ThorpPoint(
                id="ruin_check",
                label="Ruin Check (-25% Sim)",
                status=_INSUFFICIENT,
                key_metric="market_value missing",
                detail="Cannot simulate without position market_value.",
            )

        loss_25 = market_value * 0.25
        loss_pct_nlv = (loss_25 / nlv) * 100.0

        if loss_pct_nlv > 10.0:
            status = _RISK
            detail = (
                f"-25% drop = ${loss_25:,.0f} loss = {loss_pct_nlv:.1f}% of NLV "
                f"(>{10}% threshold). Reduce position."
            )
        elif loss_pct_nlv > 5.0:
            status = _CAUTION
            detail = (
                f"-25% drop = ${loss_25:,.0f} = {loss_pct_nlv:.1f}% of NLV. "
                f"Approaching 10% ruin threshold."
            )
        else:
            status = _EDGE
            detail = (
                f"-25% drop = ${loss_25:,.0f} = {loss_pct_nlv:.1f}% of NLV. "
                f"Within safe zone."
            )

        return ThorpPoint(
            id="ruin_check",
            label="Ruin Check (-25% Sim)",
            status=status,
            key_metric=f"-25%: -${loss_25:,.0f} ({loss_pct_nlv:.1f}% NLV)",
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Point 5: Fraud Scan
    # ------------------------------------------------------------------

    def _fraud_scan(self, opp: Dict, stock_data: Dict) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_fraud_scan - DEBUG - start")

        flags: List[str] = []
        status = _EDGE

        vol = _safe_float(opp.get("volume") or stock_data.get("option_volume"))
        avg_vol = _safe_float(
            opp.get("avg_volume") or stock_data.get("avg_option_volume")
        )

        if vol is not None and avg_vol is not None and avg_vol > 0:
            ratio = vol / avg_vol
            if ratio > 3.0:
                flags.append(f"option vol {ratio:.1f}x avg (unusual activity)")
                status = _CAUTION
            else:
                flags.append(f"option vol {ratio:.1f}x avg (normal)")
        else:
            flags.append("option volume data unavailable")

        premium = _safe_float(opp.get("premium") or opp.get("mid_price"))
        bs_value = _safe_float(opp.get("theoretical_value") or stock_data.get("bs_theoretical"))

        if premium is not None and bs_value is not None and bs_value > 0:
            overprice_pct = ((premium - bs_value) / bs_value) * 100.0
            if overprice_pct > 30.0:
                flags.append(f"premium {overprice_pct:.0f}% above BS theoretical (data error?)")
                status = _CAUTION
            else:
                flags.append(f"premium {overprice_pct:+.0f}% vs BS")
        else:
            flags.append("BS theoretical not available")

        liquidity_grade = (opp.get("liquidity_grade") or stock_data.get("liquidity_grade") or "").upper()
        if liquidity_grade == "D":
            flags.append("liquidity grade D — execution quality risk")
            status = _RISK

        if not flags or all("unavailable" in f or "not available" in f for f in flags):
            return ThorpPoint(
                id="fraud_scan",
                label="Fraud Scan",
                status=_INSUFFICIENT,
                key_metric="No volume/premium data",
                detail="volume and BS theoretical values not in stored opportunity.",
            )

        return ThorpPoint(
            id="fraud_scan",
            label="Fraud Scan",
            status=status,
            key_metric=flags[0],
            detail=" | ".join(flags),
        )

    # ------------------------------------------------------------------
    # Point 6: Compounding Review
    # ------------------------------------------------------------------

    def _compounding_review(
        self, trades: List[Dict], opp: Dict, baseline: float
    ) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_compounding_review - DEBUG - start")

        ann_yield = _safe_float(opp.get("annualized_yield_pct"))
        closed = [t for t in trades if _trade_is_closed(t)]

        if ann_yield is None and not closed:
            return ThorpPoint(
                id="compounding_review",
                label="Compounding Review",
                status=_INSUFFICIENT,
                key_metric="No yield data",
                detail="annualized_yield_pct and closed trades unavailable.",
            )

        avg_days = None
        if closed:
            hold_days = [_trade_hold_days(t) for t in closed if _trade_hold_days(t) is not None]
            avg_days = sum(hold_days) / len(hold_days) if hold_days else None

        baseline_pct = baseline * 100.0

        if ann_yield is not None and avg_days is not None:
            is_drag = avg_days > 180 and ann_yield < baseline_pct
            if is_drag:
                status = _CAUTION
                detail = (
                    f"Held avg {avg_days:.0f}d with {ann_yield:.1f}% ann yield "
                    f"< {baseline_pct:.1f}% baseline — compounding drag."
                )
            elif ann_yield >= baseline_pct:
                status = _EDGE
                detail = (
                    f"{ann_yield:.1f}% ann yield beats {baseline_pct:.1f}% baseline "
                    f"(avg hold {avg_days:.0f}d)."
                )
            else:
                status = _CAUTION
                detail = (
                    f"{ann_yield:.1f}% ann yield below {baseline_pct:.1f}% baseline "
                    f"(avg hold {avg_days:.0f}d)."
                )
            metric = f"{ann_yield:.1f}% ann | avg {avg_days:.0f}d held"
        elif ann_yield is not None:
            status = _EDGE if ann_yield >= baseline_pct else _CAUTION
            detail = f"Ann yield {ann_yield:.1f}% vs {baseline_pct:.1f}% baseline (hold days N/A)."
            metric = f"{ann_yield:.1f}% annualized"
        else:
            status = _CAUTION
            detail = f"Avg hold {avg_days:.0f}d — annualized yield not computed."
            metric = f"avg {avg_days:.0f}d hold"

        return ThorpPoint(
            id="compounding_review",
            label="Compounding Review",
            status=status,
            key_metric=metric,
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Point 7: Adaptability Check
    # ------------------------------------------------------------------

    def _adaptability_check(self, trades: List[Dict], symbol: str) -> ThorpPoint:
        logger.debug(
            "thorp_service-ThorpService-_adaptability_check - DEBUG - symbol=%s",
            symbol,
        )

        closed = [t for t in trades if _trade_is_closed(t)]
        if len(closed) < 3:
            return ThorpPoint(
                id="adaptability_check",
                label="Adaptability Check",
                status=_INSUFFICIENT,
                key_metric="<3 closed trades",
                detail="Need at least 3 closed trades for trend slope.",
            )

        recent = closed[:4]
        yields = [_trade_yield_pct(t) for t in recent]

        if len(yields) < 2:
            return ThorpPoint(
                id="adaptability_check",
                label="Adaptability Check",
                status=_INSUFFICIENT,
                key_metric="No yield data",
                detail="yield_pct missing from trade records.",
            )

        slope = _linear_slope(yields)
        slope_per_cycle = slope

        if slope_per_cycle < -0.15:
            status = _CAUTION
            detail = (
                f"Yield slope {slope_per_cycle:+.2f}%/cycle over last {len(yields)} trades "
                f"— edge may be decaying."
            )
        else:
            status = _EDGE
            detail = (
                f"Yield slope {slope_per_cycle:+.2f}%/cycle over last {len(yields)} trades "
                f"— no significant edge decay."
            )

        return ThorpPoint(
            id="adaptability_check",
            label="Adaptability Check",
            status=status,
            key_metric=f"slope={slope_per_cycle:+.2f}%/cycle (n={len(yields)})",
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Point 8: Independence Test
    # ------------------------------------------------------------------

    def _independence_test(self, stock_data: Dict) -> ThorpPoint:
        logger.debug("thorp_service-ThorpService-_independence_test - DEBUG - start")

        sentiment = _safe_float(
            stock_data.get("news_sentiment")
            or (stock_data.get("profile") or {}).get("news_sentiment")
        )
        markov_raw = stock_data.get("markov_prediction")

        if sentiment is None or markov_raw is None:
            return ThorpPoint(
                id="independence_test",
                label="Independence Test",
                status=_INSUFFICIENT,
                key_metric="No sentiment/Markov data",
                detail="news_sentiment or markov_prediction not in stock_data.",
            )

        markov_direction = _markov_direction(markov_raw)
        sentiment_direction = "bullish" if sentiment > 0 else "bearish"
        sentiment_conviction = abs(sentiment)

        crowded = (
            markov_direction == sentiment_direction
            and sentiment_conviction > 0.70
        )

        if crowded:
            status = _CAUTION
            detail = (
                f"Crowded consensus: sentiment {sentiment_direction} "
                f"{sentiment_conviction*100:.0f}% + Markov agree — "
                f"increase margin of safety."
            )
        else:
            status = _EDGE
            detail = (
                f"Sentiment {sentiment_direction} {sentiment_conviction*100:.0f}% "
                f"vs Markov {markov_direction} — no crowded consensus."
            )

        return ThorpPoint(
            id="independence_test",
            label="Independence Test",
            status=status,
            key_metric=f"sentiment={sentiment:.2f} markov={markov_direction}",
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Point 9: Circle of Competence
    # ------------------------------------------------------------------

    def _circle_of_competence(self, trades: List[Dict]) -> ThorpPoint:
        logger.debug(
            "thorp_service-ThorpService-_circle_of_competence - DEBUG - trade_count=%d",
            len(trades),
        )

        closed = [t for t in trades if _trade_is_closed(t)]
        if not closed:
            return ThorpPoint(
                id="circle_of_competence",
                label="Circle of Competence",
                status=_INSUFFICIENT,
                key_metric="No closed trades",
                detail="No trade history to determine competence category.",
            )

        asset_class = _most_common(
            [str(t.get("asset_class") or t.get("AssetClass") or "STK") for t in closed]
        )
        strategy = _most_common(
            [str(t.get("strategy") or t.get("Strategy") or "Unknown") for t in closed]
        )

        same_cat = [
            t
            for t in closed
            if (
                str(t.get("asset_class") or t.get("AssetClass") or "STK") == asset_class
                and str(t.get("strategy") or t.get("Strategy") or "Unknown") == strategy
            )
        ]

        n = len(same_cat)
        if n < 5:
            return ThorpPoint(
                id="circle_of_competence",
                label="Circle of Competence",
                status=_RISK,
                key_metric=f"n={n} <5 samples",
                detail=f"Only {n} {asset_class}/{strategy} trades — insufficient history.",
            )

        win_rate = sum(1 for t in same_cat if _trade_pnl(t) > 0) / n

        if win_rate > 0.60:
            status = _EDGE
        elif win_rate >= 0.40:
            status = _CAUTION
        else:
            status = _RISK

        return ThorpPoint(
            id="circle_of_competence",
            label="Circle of Competence",
            status=status,
            key_metric=f"Win rate {win_rate*100:.0f}% (n={n}) {asset_class}/{strategy}",
            detail=f"{win_rate*100:.0f}% win rate in {asset_class} {strategy} category from {n} trades.",
        )

    # ------------------------------------------------------------------
    # Point 10: Thorp Decision
    # ------------------------------------------------------------------

    def _thorp_decision(self, points: List[ThorpPoint]) -> List[ThorpDecision]:
        logger.debug("thorp_service-ThorpService-_thorp_decision - DEBUG - start")

        point_map = {p.id: p for p in points}

        weights = {
            "edge_audit": 2,
            "ruin_check": 2,
            "position_sizing": 1,
            "inefficiency_map": 1,
            "fraud_scan": 1,
            "compounding_review": 1,
            "adaptability_check": 1,
            "independence_test": 1,
            "circle_of_competence": 1,
        }

        score_map = {_EDGE: 1, _CAUTION: 0, _RISK: -1, _INSUFFICIENT: 0, _PENDING: 0}

        weighted_score = 0.0
        total_weight = 0.0
        for pid, w in weights.items():
            p = point_map.get(pid)
            if p:
                weighted_score += score_map[p.status] * w
                total_weight += w

        normalized = weighted_score / total_weight if total_weight > 0 else 0.0

        ruin = point_map.get("ruin_check")
        edge = point_map.get("edge_audit")
        kelly = point_map.get("position_sizing")
        adapt = point_map.get("adaptability_check")
        competence = point_map.get("circle_of_competence")

        ruin_is_ok = ruin is None or ruin.status in (_EDGE, _CAUTION, _INSUFFICIENT)
        ruin_is_risk = ruin is not None and ruin.status == _RISK

        decisions: List[ThorpDecision] = []

        # Action 1 — primary recommendation
        if ruin_is_risk:
            decisions.append(
                ThorpDecision(
                    rank=1,
                    action="Reduce position to eliminate ruin risk",
                    edge="Ruin Check flagged: simulated -25% loss exceeds 10% of NLV.",
                    risk="Leaving premium income on the table; potential early assignment.",
                    first_step="Place GTC limit order to close enough contracts to bring exposure under 10% NLV.",
                )
            )
        elif normalized >= 0.5 and ruin_is_ok:
            decisions.append(
                ThorpDecision(
                    rank=1,
                    action="Increase position toward Half-Kelly target",
                    edge="Edge Audit + Circle of Competence confirm proven edge in this category.",
                    risk="Over-sizing if win rate estimate is optimistic — cap at Half-Kelly.",
                    first_step="Calculate Half-Kelly NLV% and add contracts up to that limit on next expiry cycle.",
                )
            )
        else:
            decisions.append(
                ThorpDecision(
                    rank=1,
                    action="Hold current position — no scale-up until edge confirmed",
                    edge="Mixed signals: insufficient data or borderline edge metrics.",
                    risk="Missed premium income if edge proves valid.",
                    first_step="Run Live Analysis to refresh stock_data and recheck Thorp Audit.",
                )
            )

        # Action 2 — roll / adjust signal
        adapt_decay = adapt is not None and adapt.status == _CAUTION
        kelly_over = kelly is not None and kelly.status == _CAUTION
        if adapt_decay or kelly_over:
            decisions.append(
                ThorpDecision(
                    rank=2,
                    action="Roll or adjust to restore edge alignment",
                    edge="Adaptability or Kelly sizing flag signals strategy drift.",
                    risk="Roll costs (bid/ask spread) may erode premium captured.",
                    first_step="Review current strike/expiry vs current IV. Roll up/out if premium > roll cost.",
                )
            )
        else:
            decisions.append(
                ThorpDecision(
                    rank=2,
                    action="Monitor — no adjustment needed this cycle",
                    edge="No adaptability decay or sizing flag active.",
                    risk="Complacency — re-audit after each expiry cycle.",
                    first_step="Set calendar reminder to re-run Thorp Audit at next expiration.",
                )
            )

        # Action 3 — exit / reduce signal
        if (
            competence is not None and competence.status == _RISK
        ) or normalized <= -0.5:
            decisions.append(
                ThorpDecision(
                    rank=3,
                    action="Exit position — outside circle of competence or negative edge",
                    edge="Circle of Competence or aggregate score indicates no reliable edge.",
                    risk="Tax event on exit; potential missed recovery if thesis changes.",
                    first_step="Close position at market open on next liquid session. Redeploy capital to higher-edge ticker.",
                )
            )
        else:
            decisions.append(
                ThorpDecision(
                    rank=3,
                    action="Continue wheel strategy — compounding in play",
                    edge="No exit signals active; compounding review within acceptable range.",
                    risk="Complacency — monitor for edge decay over next 2-3 cycles.",
                    first_step="Review Compounding Review metric after next premium collection cycle.",
                )
            )

        return decisions


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _trade_is_closed(trade: Dict) -> bool:
    status = str(trade.get("status") or trade.get("Status") or "").upper()
    has_close_date = bool(trade.get("close_date") or trade.get("CloseDate"))
    pnl = _safe_float(trade.get("realized_pnl") or trade.get("FifoPnlRealized"))
    return status in ("CLOSED", "EXPIRED", "ASSIGNED") or has_close_date or pnl is not None


def _trade_pnl(trade: Dict) -> float:
    val = _safe_float(
        trade.get("realized_pnl")
        or trade.get("FifoPnlRealized")
        or trade.get("pnl")
    )
    return val if val is not None else 0.0


def _trade_yield_pct(trade: Dict) -> float:
    val = _safe_float(
        trade.get("yield_pct")
        or trade.get("return_pct")
        or trade.get("yield")
    )
    if val is not None:
        return val
    # Fall back to computing from pnl / cost_basis
    pnl = _trade_pnl(trade)
    cost = _safe_float(trade.get("cost_basis") or trade.get("CostBasis") or trade.get("avg_cost"))
    if cost and abs(cost) > 0:
        return (pnl / abs(cost)) * 100.0
    return 0.0


def _trade_hold_days(trade: Dict) -> Optional[float]:
    open_date = trade.get("open_date") or trade.get("OpenDate")
    close_date = trade.get("close_date") or trade.get("CloseDate")
    if not open_date or not close_date:
        return None
    try:
        if isinstance(open_date, str):
            open_date = datetime.fromisoformat(open_date.replace("Z", "+00:00"))
        if isinstance(close_date, str):
            close_date = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
        return abs((close_date - open_date).days)
    except Exception:
        return None


def _linear_slope(values: List[float]) -> float:
    """Least-squares slope of sequential values (index as x)."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    numerator = sum((xs[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0 else 0.0


def _markov_direction(markov_raw: Any) -> str:
    if isinstance(markov_raw, dict):
        signal = str(markov_raw.get("signal") or markov_raw.get("direction") or "").lower()
        prob_up = _safe_float(markov_raw.get("prob_up") or markov_raw.get("probability_up"))
        if prob_up is not None:
            return "bullish" if prob_up >= 0.5 else "bearish"
        if "bull" in signal or "up" in signal:
            return "bullish"
        if "bear" in signal or "down" in signal:
            return "bearish"
    if isinstance(markov_raw, str):
        raw = markov_raw.lower()
        if "bull" in raw or "up" in raw:
            return "bullish"
        if "bear" in raw or "down" in raw:
            return "bearish"
    val = _safe_float(markov_raw)
    if val is not None:
        return "bullish" if val >= 0.5 else "bearish"
    return "neutral"


def _most_common(values: List[str]) -> str:
    if not values:
        return "Unknown"
    counts: Dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=lambda k: counts[k])
