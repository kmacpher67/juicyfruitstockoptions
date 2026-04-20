from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from app.services import juicy_service


class _MockChain:
    def __init__(self, calls_df):
        self.calls = calls_df


class _MockTicker:
    def __init__(self, options, chain_map):
        self.options = options
        self._chain_map = chain_map

    def option_chain(self, expiry):
        return _MockChain(self._chain_map[expiry])


def _sample_calls(price: float):
    strikes = [price - 1, price + 1, price + 2, price + 3, price + 4, price + 5]
    rows = []
    for idx, strike in enumerate(strikes):
        rows.append(
            {
                'strike': strike,
                'bid': 1.2 - (0.15 * idx),
                'ask': 1.35 - (0.12 * idx),
                'lastPrice': 1.25 - (0.12 * idx),
                'volume': 800 - (80 * idx),
                'openInterest': 2000 - (220 * idx),
            }
        )
    return pd.DataFrame(rows)


def test_build_chain_level_call_candidates_returns_20_for_4_dtes():
    price = 57.67
    expiries = ['2026-04-10', '2026-04-17', '2026-04-24', '2026-05-01']
    chain_map = {exp: _sample_calls(price) for exp in expiries}

    with patch('app.services.juicy_service.yf.Ticker', return_value=_MockTicker(expiries, chain_map)):
        rows = juicy_service.build_chain_level_call_candidates('BMY', price, max_dtes=4)

    assert len(rows) == 20
    assert all(r['type'] == 'CALL' for r in rows)
    assert all(r['action'] == 'SELL' for r in rows)
    assert all('liquidity_grade' in r for r in rows)
    assert all('timeframe_bucket' in r for r in rows)


def test_build_juicy_candidates_includes_chain_rows_and_heuristics():
    price = 57.67
    expiries = ['2026-04-10', '2026-04-17', '2026-04-24', '2026-05-01']
    chain_map = {exp: _sample_calls(price) for exp in expiries}

    stock = {
        'Ticker': 'BMY',
        'Current Price': price,
        'IV Rank': 52,
        'Call/Put Skew': 1.03,
        'TSMOM_60': -0.04,
        'Annual Yield Call Prem': 9.5,
        'Annual Yield Put Prem': 11.1,
        '_last_persisted_at': datetime.now(timezone.utc).isoformat(),
    }

    with patch('app.services.juicy_service.yf.Ticker', return_value=_MockTicker(expiries, chain_map)):
        rows = juicy_service.build_juicy_candidates(stock, 'BMY', include_chain_rows=True)

    assert len(rows) >= 23
    strategies = {r['strategy'] for r in rows}
    assert 'Covered Call' in strategies
    assert 'Cash Secured Put' in strategies
    assert 'Hold / Wait' in strategies
    assert any(r.get('wheel_phase') == 'COVERED_CALL' for r in rows if r['strategy'] != 'Hold / Wait')
    assert any((r.get('annualized_return_pct') or 0) > 20 for r in rows if r['strategy'] != 'Hold / Wait')


def test_liquidity_grade_thresholds():
    assert juicy_service._liquidity_grade(900, 2000, 0.02) == 'A'  # pylint: disable=protected-access
    assert juicy_service._liquidity_grade(150, 500, 0.06) == 'B'  # pylint: disable=protected-access
    assert juicy_service._liquidity_grade(20, 80, 0.15) == 'C'  # pylint: disable=protected-access
    assert juicy_service._liquidity_grade(1, 5, 0.4) == 'D'  # pylint: disable=protected-access


def test_chain_score_prefers_short_dte_with_liquidity_penalty():
    short_good = juicy_service._chain_score(  # pylint: disable=protected-access
        annualized_yield_pct=95.0,
        dte=5,
        liquidity_grade='A',
        spread_pct_mid=0.02,
    )
    long_good = juicy_service._chain_score(  # pylint: disable=protected-access
        annualized_yield_pct=95.0,
        dte=45,
        liquidity_grade='A',
        spread_pct_mid=0.02,
    )
    short_bad_liquidity = juicy_service._chain_score(  # pylint: disable=protected-access
        annualized_yield_pct=95.0,
        dte=5,
        liquidity_grade='D',
        spread_pct_mid=0.25,
    )

    assert short_good > long_good
    assert short_bad_liquidity < short_good
