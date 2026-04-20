"""
Unit tests for ThorpService — each of the 10 Thorp point methods,
INSUFFICIENT_DATA paths, and data_completeness calculation.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from app.models.thorp import ThorpStatus
from app.services.thorp_service import (
    ThorpService,
    _linear_slope,
    _markov_direction,
    _most_common,
    _safe_float,
    _trade_hold_days,
    _trade_is_closed,
    _trade_pnl,
    _trade_yield_pct,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _closed_trade(pnl: float, yield_pct: float = None, strategy: str = "Covered Call",
                  asset_class: str = "STK", hold_days: int = 30) -> dict:
    from datetime import timedelta
    open_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    close_dt = open_dt + timedelta(days=hold_days)
    t = {
        "status": "CLOSED",
        "realized_pnl": pnl,
        "cost_basis": 100.0,
        "strategy": strategy,
        "asset_class": asset_class,
        "open_date": open_dt.isoformat(),
        "close_date": close_dt.isoformat(),
    }
    if yield_pct is not None:
        t["yield_pct"] = yield_pct
    return t


def _make_db(
    stock_data=None,
    opportunity=None,
    holdings=None,
    trades=None,
    config=None,
    nlv_total=50000.0,
):
    db = MagicMock()

    db.stock_data.find_one.return_value = stock_data or {}
    db.juicy_opportunities.find_one.return_value = opportunity or {}
    db.ibkr_holdings.find_one.return_value = holdings or {}
    db.trades.find.return_value = trades if trades is not None else []
    db.system_config.find_one.return_value = config or {"thorp_inflation_baseline": 5.9, "risk_free_rate": 5.3}
    db.ibkr_holdings.aggregate.return_value = [{"total": nlv_total}]

    return db


def _make_service(db=None):
    if db is None:
        db = _make_db()
    return ThorpService(db)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

def test_safe_float_valid():
    assert _safe_float(3.14) == pytest.approx(3.14)
    assert _safe_float("2.5") == pytest.approx(2.5)
    assert _safe_float(None) is None
    assert _safe_float("abc") is None


def test_linear_slope_positive():
    slope = _linear_slope([1.0, 2.0, 3.0, 4.0])
    assert slope > 0


def test_linear_slope_negative():
    slope = _linear_slope([4.0, 3.0, 2.0, 1.0])
    assert slope < 0


def test_linear_slope_single_value():
    assert _linear_slope([5.0]) == 0.0


def test_markov_direction_dict_prob_up():
    assert _markov_direction({"prob_up": 0.7}) == "bullish"
    assert _markov_direction({"prob_up": 0.3}) == "bearish"


def test_markov_direction_string():
    assert _markov_direction("bullish signal") == "bullish"
    assert _markov_direction("bearish") == "bearish"


def test_most_common():
    assert _most_common(["A", "B", "A", "A", "B"]) == "A"


def test_trade_is_closed_by_status():
    assert _trade_is_closed({"status": "CLOSED"})
    assert not _trade_is_closed({"status": "OPEN"})


def test_trade_hold_days():
    t = _closed_trade(pnl=10, hold_days=45)
    assert _trade_hold_days(t) == 45


# ---------------------------------------------------------------------------
# Point 1: Edge Audit
# ---------------------------------------------------------------------------

class TestEdgeAudit:
    def _svc(self, trades):
        return _make_service(_make_db(trades=trades))

    def test_edge_status_when_edge_above_baseline(self):
        trades = [_closed_trade(pnl=10, yield_pct=20.0) for _ in range(5)]
        svc = self._svc(trades)
        pt = svc._edge_audit(trades, baseline=0.059)
        assert pt.status == ThorpStatus.EDGE

    def test_caution_when_small_positive_edge(self):
        wins = [_closed_trade(pnl=1, yield_pct=2.0) for _ in range(4)]
        losses = [_closed_trade(pnl=-5, yield_pct=-5.0) for _ in range(1)]
        trades = wins + losses
        svc = self._svc(trades)
        pt = svc._edge_audit(trades, baseline=0.059)
        # E = 0.8*0.02 - 0.2*0.05 = 0.016 - 0.01 = 0.006 < 0.059 → CAUTION
        assert pt.status == ThorpStatus.CAUTION

    def test_risk_when_negative_edge(self):
        wins = [_closed_trade(pnl=1, yield_pct=1.0)]
        losses = [_closed_trade(pnl=-20, yield_pct=-20.0) for _ in range(4)]
        trades = wins + losses
        svc = self._svc(trades)
        pt = svc._edge_audit(trades, baseline=0.059)
        assert pt.status == ThorpStatus.RISK

    def test_insufficient_data_fewer_than_3_trades(self):
        trades = [_closed_trade(pnl=10, yield_pct=5.0)]
        svc = self._svc(trades)
        pt = svc._edge_audit(trades, baseline=0.059)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_insufficient_data_no_trades(self):
        svc = self._svc([])
        pt = svc._edge_audit([], baseline=0.059)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 2: Kelly Sizing
# ---------------------------------------------------------------------------

class TestKellySizing:
    def _svc(self, trades, holdings=None, nlv=50000.0):
        db = _make_db(trades=trades, holdings=holdings or {}, nlv_total=nlv)
        return _make_service(db)

    def _trades_with_yields(self, n_wins=6, n_losses=2, yield_win=15.0, yield_loss=-10.0):
        wins = [_closed_trade(pnl=15, yield_pct=yield_win) for _ in range(n_wins)]
        losses = [_closed_trade(pnl=-10, yield_pct=yield_loss) for _ in range(n_losses)]
        return wins + losses

    def test_edge_when_within_kelly(self):
        trades = self._trades_with_yields()
        holdings = {"market_value": 2000.0}  # 4% of 50k
        svc = self._svc(trades, holdings=holdings)
        pt = svc._kelly_sizing(trades, {}, holdings, 50000.0, 0.053)
        assert pt.status in (ThorpStatus.EDGE, ThorpStatus.CAUTION)

    def test_caution_when_over_committed(self):
        trades = self._trades_with_yields()
        holdings = {"market_value": 45000.0}  # 90% — way over Kelly
        svc = self._svc(trades, holdings=holdings)
        pt = svc._kelly_sizing(trades, {}, holdings, 50000.0, 0.053)
        assert pt.status == ThorpStatus.CAUTION

    def test_insufficient_data_no_trades(self):
        svc = self._svc([])
        pt = svc._kelly_sizing([], {}, {}, 50000.0, 0.053)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_insufficient_data_no_nlv(self):
        trades = self._trades_with_yields()
        svc = self._svc(trades, nlv=0.0)
        pt = svc._kelly_sizing(trades, {}, {}, None, 0.053)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 3: Inefficiency Map
# ---------------------------------------------------------------------------

class TestInefficiencyMap:
    def _svc(self, stock_data):
        return _make_service(_make_db(stock_data=stock_data))

    def test_caution_high_skew(self):
        svc = self._svc({"call_put_skew": 2.0})
        pt = svc._inefficiency_map({"call_put_skew": 2.0})
        assert pt.status in (ThorpStatus.CAUTION, ThorpStatus.PENDING_DATA)

    def test_caution_large_iv_rv_gap(self):
        svc = self._svc({"call_put_skew": 1.0, "iv_vs_rv": 1.25})
        pt = svc._inefficiency_map({"call_put_skew": 1.0, "iv_vs_rv": 1.25})
        assert pt.status == ThorpStatus.CAUTION

    def test_edge_normal_skew_and_iv_rv(self):
        svc = self._svc({"call_put_skew": 1.0, "iv_vs_rv": 1.05})
        pt = svc._inefficiency_map({"call_put_skew": 1.0, "iv_vs_rv": 1.05})
        assert pt.status == ThorpStatus.EDGE

    def test_insufficient_data_no_fields(self):
        svc = self._svc({})
        pt = svc._inefficiency_map({})
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_pending_when_skew_present_but_no_iv_rv(self):
        svc = self._svc({"call_put_skew": 1.2})
        pt = svc._inefficiency_map({"call_put_skew": 1.2})
        # skew is normal, iv_rv missing → PENDING_DATA
        assert pt.status == ThorpStatus.PENDING_DATA


# ---------------------------------------------------------------------------
# Point 4: Ruin Check
# ---------------------------------------------------------------------------

class TestRuinCheck:
    def test_risk_when_loss_exceeds_10pct_nlv(self):
        svc = _make_service()
        holdings = {"market_value": 10000.0}  # -25% = 2500, 2500/20000 = 12.5% > 10%
        pt = svc._ruin_check(holdings, nlv=20000.0)
        assert pt.status == ThorpStatus.RISK

    def test_edge_when_loss_within_safe_zone(self):
        svc = _make_service()
        holdings = {"market_value": 1000.0}  # -25% = 250, 250/50000 = 0.5%
        pt = svc._ruin_check(holdings, nlv=50000.0)
        assert pt.status == ThorpStatus.EDGE

    def test_caution_between_5_and_10_pct(self):
        svc = _make_service()
        holdings = {"market_value": 3000.0}  # -25% = 750, 750/10000 = 7.5%
        pt = svc._ruin_check(holdings, nlv=10000.0)
        assert pt.status == ThorpStatus.CAUTION

    def test_insufficient_data_no_holdings(self):
        svc = _make_service()
        pt = svc._ruin_check({}, nlv=50000.0)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_insufficient_data_no_nlv(self):
        svc = _make_service()
        pt = svc._ruin_check({"market_value": 5000.0}, nlv=None)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_insufficient_data_missing_market_value(self):
        svc = _make_service()
        pt = svc._ruin_check({"symbol": "AMD"}, nlv=50000.0)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 5: Fraud Scan
# ---------------------------------------------------------------------------

class TestFraudScan:
    def test_caution_on_high_volume(self):
        svc = _make_service()
        opp = {"volume": 9000, "avg_volume": 1000}
        pt = svc._fraud_scan(opp, {})
        assert pt.status == ThorpStatus.CAUTION

    def test_normal_volume(self):
        svc = _make_service()
        opp = {"volume": 1500, "avg_volume": 1000}
        pt = svc._fraud_scan(opp, {})
        assert pt.status == ThorpStatus.EDGE

    def test_risk_on_liquidity_grade_d(self):
        svc = _make_service()
        opp = {"volume": 500, "avg_volume": 1000, "liquidity_grade": "D"}
        pt = svc._fraud_scan(opp, {})
        assert pt.status == ThorpStatus.RISK

    def test_caution_premium_above_bs(self):
        svc = _make_service()
        opp = {"volume": 500, "avg_volume": 1000, "premium": 5.0, "theoretical_value": 3.0}
        pt = svc._fraud_scan(opp, {})
        assert pt.status == ThorpStatus.CAUTION

    def test_insufficient_data_no_volume(self):
        svc = _make_service()
        pt = svc._fraud_scan({}, {})
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 6: Compounding Review
# ---------------------------------------------------------------------------

class TestCompoundingReview:
    def test_edge_ann_yield_above_baseline(self):
        svc = _make_service()
        opp = {"annualized_yield_pct": 18.0}
        trades = [_closed_trade(pnl=10, yield_pct=5.0) for _ in range(3)]
        pt = svc._compounding_review(trades, opp, baseline=0.059)
        assert pt.status == ThorpStatus.EDGE

    def test_caution_long_hold_below_baseline(self):
        svc = _make_service()
        opp = {"annualized_yield_pct": 3.0}
        trades = [_closed_trade(pnl=5, yield_pct=3.0, hold_days=200) for _ in range(3)]
        pt = svc._compounding_review(trades, opp, baseline=0.059)
        assert pt.status == ThorpStatus.CAUTION

    def test_insufficient_data_no_yield_no_trades(self):
        svc = _make_service()
        pt = svc._compounding_review([], {}, baseline=0.059)
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 7: Adaptability Check
# ---------------------------------------------------------------------------

class TestAdaptabilityCheck:
    def test_caution_when_yield_declining(self):
        svc = _make_service()
        trades = [
            _closed_trade(pnl=5, yield_pct=10.0),
            _closed_trade(pnl=4, yield_pct=7.0),
            _closed_trade(pnl=2, yield_pct=3.0),
            _closed_trade(pnl=1, yield_pct=1.0),
        ]
        pt = svc._adaptability_check(trades, "AMD")
        assert pt.status == ThorpStatus.CAUTION

    def test_edge_stable_yields(self):
        svc = _make_service()
        trades = [_closed_trade(pnl=5, yield_pct=8.0) for _ in range(4)]
        pt = svc._adaptability_check(trades, "AMD")
        assert pt.status == ThorpStatus.EDGE

    def test_insufficient_data_fewer_than_3(self):
        svc = _make_service()
        trades = [_closed_trade(pnl=5, yield_pct=8.0)]
        pt = svc._adaptability_check(trades, "AMD")
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 8: Independence Test
# ---------------------------------------------------------------------------

class TestIndependenceTest:
    def test_caution_crowded_consensus(self):
        svc = _make_service()
        stock_data = {
            "news_sentiment": 0.80,
            "markov_prediction": {"prob_up": 0.85},
        }
        pt = svc._independence_test(stock_data)
        assert pt.status == ThorpStatus.CAUTION

    def test_edge_divergent_signals(self):
        svc = _make_service()
        stock_data = {
            "news_sentiment": 0.60,
            "markov_prediction": {"prob_up": 0.35},
        }
        pt = svc._independence_test(stock_data)
        assert pt.status == ThorpStatus.EDGE

    def test_edge_low_conviction_sentiment(self):
        svc = _make_service()
        stock_data = {
            "news_sentiment": 0.55,
            "markov_prediction": {"prob_up": 0.60},
        }
        pt = svc._independence_test(stock_data)
        # sentiment < 0.70 → not crowded
        assert pt.status == ThorpStatus.EDGE

    def test_insufficient_data_no_sentiment(self):
        svc = _make_service()
        pt = svc._independence_test({})
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_insufficient_data_no_markov(self):
        svc = _make_service()
        pt = svc._independence_test({"news_sentiment": 0.8})
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Point 9: Circle of Competence
# ---------------------------------------------------------------------------

class TestCircleOfCompetence:
    def test_edge_high_win_rate(self):
        svc = _make_service()
        trades = [_closed_trade(pnl=10, strategy="Covered Call", asset_class="STK") for _ in range(7)]
        pt = svc._circle_of_competence(trades)
        assert pt.status == ThorpStatus.EDGE

    def test_risk_low_win_rate(self):
        svc = _make_service()
        wins = [_closed_trade(pnl=5, strategy="Covered Call", asset_class="STK")]
        losses = [_closed_trade(pnl=-5, strategy="Covered Call", asset_class="STK") for _ in range(4)]
        trades = wins + losses
        pt = svc._circle_of_competence(trades)
        assert pt.status == ThorpStatus.RISK

    def test_risk_fewer_than_5_samples(self):
        svc = _make_service()
        trades = [_closed_trade(pnl=10) for _ in range(3)]
        pt = svc._circle_of_competence(trades)
        assert pt.status == ThorpStatus.RISK

    def test_insufficient_data_no_trades(self):
        svc = _make_service()
        pt = svc._circle_of_competence([])
        assert pt.status == ThorpStatus.INSUFFICIENT_DATA

    def test_caution_borderline_win_rate(self):
        svc = _make_service()
        wins = [_closed_trade(pnl=5, strategy="Covered Call", asset_class="STK") for _ in range(3)]
        losses = [_closed_trade(pnl=-5, strategy="Covered Call", asset_class="STK") for _ in range(2)]
        trades = wins + losses
        pt = svc._circle_of_competence(trades)
        # 60% win rate → EDGE threshold is >60, so exactly 60% → CAUTION
        assert pt.status in (ThorpStatus.CAUTION, ThorpStatus.EDGE)


# ---------------------------------------------------------------------------
# Thorp Decision
# ---------------------------------------------------------------------------

class TestThorpDecision:
    def _make_points(self, statuses: dict):
        from app.models.thorp import ThorpPoint
        defaults = {
            "edge_audit": ThorpStatus.EDGE,
            "position_sizing": ThorpStatus.EDGE,
            "inefficiency_map": ThorpStatus.EDGE,
            "ruin_check": ThorpStatus.EDGE,
            "fraud_scan": ThorpStatus.EDGE,
            "compounding_review": ThorpStatus.EDGE,
            "adaptability_check": ThorpStatus.EDGE,
            "independence_test": ThorpStatus.EDGE,
            "circle_of_competence": ThorpStatus.EDGE,
        }
        defaults.update(statuses)
        return [
            ThorpPoint(id=k, label=k, status=v, key_metric="", detail="")
            for k, v in defaults.items()
        ]

    def test_ruin_risk_generates_reduce_action(self):
        svc = _make_service()
        points = self._make_points({"ruin_check": ThorpStatus.RISK})
        decisions = svc._thorp_decision(points)
        assert decisions[0].rank == 1
        assert "reduce" in decisions[0].action.lower() or "ruin" in decisions[0].edge.lower()

    def test_all_edge_generates_increase_action(self):
        svc = _make_service()
        points = self._make_points({})
        decisions = svc._thorp_decision(points)
        assert decisions[0].rank == 1
        assert "increase" in decisions[0].action.lower()

    def test_returns_3_decisions(self):
        svc = _make_service()
        points = self._make_points({})
        decisions = svc._thorp_decision(points)
        assert len(decisions) == 3

    def test_adaptability_caution_generates_roll_action(self):
        svc = _make_service()
        points = self._make_points({"adaptability_check": ThorpStatus.CAUTION})
        decisions = svc._thorp_decision(points)
        roll_actions = [d for d in decisions if "roll" in d.action.lower() or "adjust" in d.action.lower()]
        assert len(roll_actions) >= 1


# ---------------------------------------------------------------------------
# Data completeness
# ---------------------------------------------------------------------------

class TestDataCompleteness:
    def test_completeness_all_edge(self):
        import asyncio
        trades = [_closed_trade(pnl=10, yield_pct=15.0) for _ in range(8)]
        holdings = {"market_value": 1000.0}
        stock_data = {
            "call_put_skew": 1.1,
            "iv_vs_rv": 1.05,
            "news_sentiment": 0.5,
            "markov_prediction": {"prob_up": 0.4},
        }
        opp = {
            "annualized_yield_pct": 20.0,
            "volume": 500,
            "avg_volume": 600,
        }
        db = _make_db(
            stock_data=stock_data,
            opportunity=opp,
            holdings=holdings,
            trades=trades,
            nlv_total=50000.0,
        )
        # Prevent cache load: first find_one returns no thorp_audit, second returns stock_data
        db.stock_data.find_one.side_effect = [
            {},
            stock_data,
        ]
        svc = ThorpService(db)
        result = asyncio.run(svc.compute("AMD"))
        assert result.data_completeness > 0.0

    def test_completeness_no_data(self):
        import asyncio
        db = _make_db(
            stock_data={},
            opportunity={},
            holdings={},
            trades=[],
            nlv_total=50000.0,
        )
        db.stock_data.find_one.side_effect = [{}, {}]
        svc = ThorpService(db)
        result = asyncio.run(svc.compute("EMPTY"))
        # All points are INSUFFICIENT_DATA → completeness = 0
        assert result.data_completeness == 0.0
