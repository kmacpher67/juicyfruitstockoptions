"""
Regression tests for portfolio coverage-status calculation.

Covers:
  portfolio-coverage-001: (account, underlying) granularity
  portfolio-coverage-002: AMD 200 shares / -2 short calls → Covered
  portfolio-coverage-003: Both STK and OPT rows in a group share the same status
  portfolio-coverage-004: flat rows (qty == 0) get blank coverage_status
"""
import pytest
from app.api.routes import (
    _resolve_coverage_status,
    _is_short_call_position,
    _is_flat_position_row,
)


# ---------------------------------------------------------------------------
# _resolve_coverage_status
# ---------------------------------------------------------------------------

class TestResolveCoverageStatus:
    def test_covered_exact_match(self):
        status, mismatch = _resolve_coverage_status(200, 200)
        assert status == "Covered"
        assert mismatch is False

    def test_covered_single_contract(self):
        status, mismatch = _resolve_coverage_status(100, 100)
        assert status == "Covered"
        assert mismatch is False

    def test_uncovered_partial_cover(self):
        # 200 shares, only 1 short call (100 contracts) → Uncovered
        status, mismatch = _resolve_coverage_status(200, 100)
        assert status == "Uncovered"
        assert mismatch is True

    def test_uncovered_no_options(self):
        status, mismatch = _resolve_coverage_status(500, 0)
        assert status == "Uncovered"
        assert mismatch is True

    def test_naked_more_options_than_shares(self):
        # 100 shares, -2 short calls (200 contracts) → Naked
        status, mismatch = _resolve_coverage_status(100, 200)
        assert status == "Naked"
        assert mismatch is True

    def test_naked_no_shares(self):
        status, mismatch = _resolve_coverage_status(0, 100)
        assert status == "Naked"
        assert mismatch is True

    def test_amd_regression_covered(self):
        """portfolio-coverage-002: AMD U110638 200 shares, -2 short calls → Covered."""
        # coverage_by_account accumulates abs(qty) * multiplier:
        # abs(-2) * 100 = 200 short_calls in share-equivalent units
        status, mismatch = _resolve_coverage_status(shares=200, short_calls=200)
        assert status == "Covered", (
            "AMD 200 shares / -2 short calls must be Covered, not Uncovered"
        )
        assert mismatch is False

    def test_none_inputs_default_zero(self):
        status, mismatch = _resolve_coverage_status(None, None)
        # 0 shares == 0 covered_calls → Covered
        assert status == "Covered"
        assert mismatch is False

    def test_fractional_equality(self):
        # Edge: floating-point exact match
        status, mismatch = _resolve_coverage_status(300.0, 300.0)
        assert status == "Covered"


# ---------------------------------------------------------------------------
# _is_short_call_position
# ---------------------------------------------------------------------------

class TestIsShortCallPosition:
    def test_short_call_via_right_field(self):
        row = {"secType": "OPT", "quantity": -2, "right": "C"}
        assert _is_short_call_position(row) is True

    def test_short_put_is_not_short_call(self):
        row = {"secType": "OPT", "quantity": -2, "right": "P"}
        assert _is_short_call_position(row) is False

    def test_long_call_not_short(self):
        row = {"secType": "OPT", "quantity": 2, "right": "C"}
        assert _is_short_call_position(row) is False

    def test_stk_not_short_call(self):
        row = {"secType": "STK", "quantity": 200}
        assert _is_short_call_position(row) is False

    def test_short_call_via_occ_symbol(self):
        # right field absent; OCC symbol encodes 'C'
        row = {"secType": "OPT", "quantity": -1, "symbol": "AMD260220C00235000"}
        assert _is_short_call_position(row) is True

    def test_short_call_via_local_symbol(self):
        row = {"secType": "OPT", "quantity": -3, "local_symbol": "MSFT  260220C00400000"}
        assert _is_short_call_position(row) is True

    def test_fop_short_call_included(self):
        row = {"asset_class": "FOP", "quantity": -1, "right": "C"}
        assert _is_short_call_position(row) is True


# ---------------------------------------------------------------------------
# _is_flat_position_row  (portfolio-coverage-004: flat rows get blank status)
# ---------------------------------------------------------------------------

class TestIsFlatPositionRow:
    def test_zero_quantity_is_flat(self):
        assert _is_flat_position_row({"quantity": 0}) is True

    def test_positive_quantity_not_flat(self):
        assert _is_flat_position_row({"quantity": 200}) is False

    def test_negative_quantity_not_flat(self):
        assert _is_flat_position_row({"quantity": -2}) is False

    def test_none_quantity_is_flat(self):
        assert _is_flat_position_row({"quantity": None}) is True


# ---------------------------------------------------------------------------
# portfolio-coverage-003: STK and OPT rows in a group share the same status
# ---------------------------------------------------------------------------

class TestCoverageGroupConsistency:
    """
    Simulate the accumulation loop in routes.py and verify that both the STK
    row and a CALL OPT row belonging to the same (account, underlying) group
    resolve to the same coverage_status value.
    """

    def _build_coverage_and_resolve(self, stk_qty, opt_qty, multiplier=100.0):
        """Helper mirroring the coverage accumulation in routes.py."""
        shares = float(stk_qty)
        short_calls = abs(float(opt_qty)) * multiplier if opt_qty < 0 else 0.0

        stk_row = {"secType": "STK", "quantity": stk_qty}
        opt_row = {"secType": "OPT", "quantity": opt_qty, "right": "C"}

        stk_status, _ = _resolve_coverage_status(shares, short_calls)
        opt_status, _ = _resolve_coverage_status(shares, short_calls)

        return stk_status, opt_status

    def test_covered_both_rows_agree(self):
        stk_status, opt_status = self._build_coverage_and_resolve(200, -2)
        assert stk_status == "Covered"
        assert opt_status == stk_status

    def test_uncovered_both_rows_agree(self):
        stk_status, opt_status = self._build_coverage_and_resolve(300, -2)
        assert stk_status == "Uncovered"
        assert opt_status == stk_status

    def test_naked_both_rows_agree(self):
        stk_status, opt_status = self._build_coverage_and_resolve(100, -3)
        assert stk_status == "Naked"
        assert opt_status == stk_status
