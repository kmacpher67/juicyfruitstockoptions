import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.api import routes

from app.models import User

class _RouteResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _RouteClient:
    def get(self, path: str):
        assert path == "/api/portfolio/holdings"
        payload = asyncio.run(
            routes.get_portfolio_holdings(
                current_user=User(username="testuser", role="admin", disabled=False)
            )
        )
        return _RouteResponse(200, payload)


@pytest.fixture
def client():
    """Fixture to provide a lightweight route client without app lifespan startup."""
    yield _RouteClient()

def test_get_portfolio_holdings_enrichment(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        # 1. Mock DB
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db
        
        now = datetime.now()
        snap_id = "test_snap"
        
        mock_holdings = [
            # Stock Uncovered
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 150,
                "mark_price": 160.0,
                "report_date": "2026-03-27"
            },
            # Short Call Expiring Soon & ITM
            {
                "symbol": "AAPL  260402C00150000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -1,
                "expiry": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
                "strike": 150.0,
                "mark_price": 12.5,
                "underlying_symbol": "AAPL"
            }
        ]
        
        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": snap_id}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []
        
        # 2. Mock OptionsAnalyzer
        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        # AAPL has 150 shares and 1 short call (100 shares) -> Partial or Uncovered?
        # Actually, OptionsAnalyzer._group_by_underlying would calculate this.
        # We mock the 'grouped' property that routes.py uses.
        mock_analyzer.grouped = {
            "AAPL": {
                "shares": 150,
                "short_calls": 100,
                "options": [mock_holdings[1]]
            }
        }
        
        # 3. Call API
        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()
        
        # 4. Verify Enrichment
        aapl_stk = next(h for h in data if h["asset_class"] == "STK")
        aapl_opt = next(h for h in data if h["asset_class"] == "OPT")
        
        # Coverage Status
        assert aapl_stk["coverage_status"] == "Uncovered"
        assert aapl_opt["coverage_status"] == "Uncovered" # Both get underlying status
        assert aapl_stk["coverage_mismatch"] is True
        assert aapl_opt["coverage_mismatch"] is True
        
        # DTE & Expiring Flag
        assert aapl_opt["dte"] >= 4 and aapl_opt["dte"] <= 6
        assert aapl_opt["is_expiring_soon"] == True
        
        # ITM & Distance
        assert aapl_opt["is_itm"] == True
        # strike 150, underlying 160 -> dist (160-150)/160 = 0.0625
        assert aapl_opt["dist_to_strike_pct"] == pytest.approx(0.0625, 0.001)
        assert aapl_opt["underlying_market_price"] == pytest.approx(160.0, 0.001)


def test_get_portfolio_holdings_otm_distance_uses_underlying_price_not_option_premium(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "AMD",
                "asset_class": "STK",
                "account_id": "U110638",
                "quantity": 200,
                "mark_price": 210.21,
                "report_date": "2026-04-02",
            },
            {
                "symbol": "AMD  260402C00202500",
                "asset_class": "OPT",
                "account_id": "U110638",
                "quantity": -1,
                "strike": 202.5,
                "mark_price": 8.21,
                "expiry": "2026-04-02",
                "underlying_symbol": "AMD",
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {
            "AMD": {
                "shares": 200,
                "short_calls": 100,
                "options": [mock_holdings[1]],
            }
        }

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        amd_opt = next(h for h in data if h["asset_class"] == "OPT")

        expected_distance = abs(210.21 - 202.5) / 210.21
        assert amd_opt["dist_to_strike_pct"] == pytest.approx(expected_distance, 0.001)
        assert amd_opt["dist_to_strike_pct"] == pytest.approx(0.0367, 0.001)
        assert amd_opt["underlying_market_price"] == pytest.approx(210.21, 0.001)
        assert amd_opt["is_itm"] is True


def test_get_portfolio_holdings_coverage_is_grouped_by_account(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
            {
                "symbol": "AAPL  260402C00150000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -1,
                "underlying_symbol": "AAPL"
            },
            {
                "symbol": "AAPL",
                "asset_class": "STK",
                "account_id": "U2",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {
            "AAPL": {
                "shares": 200,
                "short_calls": 100,
                "options": [mock_holdings[1]]
            }
        }

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        u1_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U1")
        u1_opt = next(h for h in data if h["asset_class"] == "OPT" and h["account_id"] == "U1")
        u2_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U2")

        assert u1_stk["coverage_status"] == "Covered"
        assert u1_stk["coverage_mismatch"] is False
        assert u1_opt["coverage_status"] == "Covered"
        assert u2_stk["coverage_status"] == "Uncovered"
        assert u2_stk["coverage_mismatch"] is True


def test_get_portfolio_holdings_marks_naked_positions_as_mismatch(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "TSLA",
                "asset_class": "STK",
                "account_id": "U1",
                "quantity": 100,
                "report_date": "2026-03-27"
            },
            {
                "symbol": "TSLA  260402C00200000",
                "asset_class": "OPT",
                "account_id": "U1",
                "quantity": -2,
                "underlying_symbol": "TSLA"
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {
            "TSLA": {
                "shares": 100,
                "short_calls": 200,
                "options": [mock_holdings[1]]
            }
        }

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        for row in data:
            assert row["coverage_status"] == "Naked"
            assert row["coverage_mismatch"] is True


def test_get_portfolio_holdings_marks_pure_stock_uncovered_when_using_sectype(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "MSFT",
                "secType": "STK",
                "account_id": "U1",
                "quantity": 200,
                "report_date": "2026-03-27"
            }
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["coverage_status"] == "Uncovered"
        assert data[0]["coverage_mismatch"] is True
        assert data[0]["covered_shares"] == 0
        assert data[0]["share_quantity_total"] == 200


def test_get_portfolio_holdings_coverage_strict_account_coverage(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {"symbol": "AAPL", "asset_class": "STK", "account_id": "U1", "quantity": 100},
            {"symbol": "AAPL  260402C00150000", "asset_class": "OPT", "account_id": "U1", "quantity": -1, "underlying_symbol": "AAPL"},
            {"symbol": "AAPL", "asset_class": "STK", "account_id": "U2", "quantity": 100}
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        u1_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U1")
        u2_stk = next(h for h in data if h["asset_class"] == "STK" and h["account_id"] == "U2")

        assert u1_stk["coverage_status"] == "Covered"
        assert u1_stk["coverage_mismatch"] is False

        assert u2_stk["coverage_status"] == "Uncovered"
        assert u2_stk["coverage_mismatch"] is True


def test_get_portfolio_holdings_normalizes_live_tws_rows(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "AMD",
                "local_symbol": "AMD   260402C00202500",
                "secType": "OPT",
                "account": "U110638",
                "position": -1,
                "avg_cost": 5.25,
                "last_trade_date": "20260402",
                "right": "C",
                "strike": 202.5,
                "source": "tws",
            },
            {
                "symbol": "AMD",
                "secType": "STK",
                "account": "U110638",
                "position": 200,
                "avg_cost": 118.55,
                "source": "tws",
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        option_row = next(h for h in data if h["security_type"] == "OPT")
        stock_row = next(h for h in data if h["security_type"] == "STK")

        assert option_row["account_id"] == "U110638"
        assert option_row["quantity"] == -1
        assert option_row["cost_basis"] == 5.25
        assert option_row["display_symbol"] == "AMD 2026-04-02 202.5 Call"
        assert option_row["percent_of_nav"] is None
        assert option_row["coverage_status"] == "Uncovered"
        assert stock_row["coverage_status"] == "Uncovered"


def test_get_portfolio_holdings_counts_tws_local_symbol_short_calls_for_covered_status(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "AMD",
                "secType": "STK",
                "account": "U110638",
                "position": 200,
                "avg_cost": 118.55,
                "source": "tws",
            },
            {
                "symbol": "AMD",
                "local_symbol": "AMD   260402C00202500",
                "secType": "OPT",
                "account": "U110638",
                "position": -1,
                "avg_cost": 5.25,
                "last_trade_date": "20260402",
                "right": "C",
                "strike": 202.5,
                "source": "tws",
            },
            {
                "symbol": "AMD",
                "local_symbol": "AMD   260410C00207500",
                "secType": "OPT",
                "account": "U110638",
                "position": -1,
                "avg_cost": 3.15,
                "last_trade_date": "20260410",
                "right": "C",
                "strike": 207.5,
                "source": "tws",
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        stock_row = next(h for h in data if h["security_type"] == "STK")
        option_rows = [h for h in data if h["security_type"] == "OPT"]

        assert stock_row["coverage_status"] == "Covered"
        assert stock_row["coverage_mismatch"] is False
        assert stock_row["share_quantity_total"] == 200
        assert stock_row["covered_shares"] == 200

        assert len(option_rows) == 2
        for option_row in option_rows:
            assert option_row["coverage_status"] == "Covered"
            assert option_row["coverage_mismatch"] is False
            assert option_row["share_quantity_total"] == 200
            assert option_row["covered_shares"] == 200


def test_get_portfolio_holdings_leaves_zero_qty_option_rows_without_coverage_label(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "ORCL",
                "secType": "STK",
                "account": "U1",
                "position": 100,
                "source": "tws",
            },
            {
                "symbol": "ORCL",
                "local_symbol": "ORCL  260402C00145000",
                "secType": "OPT",
                "account": "U1",
                "position": -1,
                "right": "C",
                "strike": 145.0,
                "last_trade_date": "20260402",
                "source": "tws",
            },
            {
                "symbol": "ORCL",
                "local_symbol": "ORCL  260402C00144000",
                "secType": "OPT",
                "account": "U1",
                "position": 0,
                "right": "C",
                "strike": 144.0,
                "last_trade_date": "20260402",
                "source": "tws",
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        stock_row = next(h for h in data if h["security_type"] == "STK")
        active_option_row = next(
            h for h in data if h["security_type"] == "OPT" and h["quantity"] == -1
        )
        flat_option_row = next(
            h for h in data if h["security_type"] == "OPT" and h["quantity"] == 0
        )

        assert stock_row["coverage_status"] == "Covered"
        assert active_option_row["coverage_status"] == "Covered"
        assert flat_option_row["coverage_status"] == ""
        assert flat_option_row["coverage_mismatch"] is False


def test_get_portfolio_holdings_percent_of_nav_remains_fraction_and_missing_values_stay_null(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {
                "symbol": "MSFT",
                "secType": "STK",
                "account_id": "U1",
                "quantity": 100,
                "percent_of_nav": 12.5,
                "market_price": None,
                "market_value": "",
                "cost_basis": None,
                "unrealized_pnl": None,
            }
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        row = response.json()[0]

        assert row["security_type"] == "STK"
        assert row["display_symbol"] == "MSFT"
        assert row["percent_of_nav"] == pytest.approx(0.125)
        assert row["market_price"] is None
        assert row["market_value"] is None
        assert row["cost_basis"] is None
        assert row["unrealized_pnl"] is None


def test_get_portfolio_holdings_merges_flex_and_tws_rows_into_one_visible_position(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls, \
         patch("app.services.options_analysis.OptionsAnalyzer") as mock_analyzer_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        live_rows = [
            {
                "symbol": "AMD",
                "local_symbol": "AMD   260402C00202500",
                "secType": "OPT",
                "account": "U110638",
                "position": -1,
                "market_price": 2.95,
                "market_value": -295.0,
                "unrealized_pnl": 180.0,
                "last_trade_date": "20260402",
                "right": "C",
                "strike": 202.5,
                "source": "tws",
            }
        ]
        flex_rows = [
            {
                "symbol": "AMD  260402C00202500",
                "asset_class": "OPT",
                "account_id": "U110638",
                "quantity": -1,
                "cost_basis": 4.75,
                "expiry": "2026-04-02",
                "right": "C",
                "strike": 202.5,
                "source": "flex",
            }
        ]

        def find_one_side_effect(query=None, sort=None):
            if query == {"source": "tws"}:
                return {"snapshot_id": "tws_snap", "source": "tws"}
            if query == {"source": "flex"}:
                return {"snapshot_id": "flex_snap", "source": "flex"}
            return None

        def find_side_effect(query, projection):
            if query == {"snapshot_id": "tws_snap", "source": "tws"}:
                return live_rows
            if query == {"snapshot_id": "flex_snap", "source": "flex"}:
                return flex_rows
            return []

        mock_db.ibkr_holdings.find_one.side_effect = find_one_side_effect
        mock_db.ibkr_holdings.find.side_effect = find_side_effect
        mock_db.ibkr_dividends.aggregate.return_value = []

        mock_analyzer = MagicMock()
        mock_analyzer_cls.return_value = mock_analyzer
        mock_analyzer.grouped = {"AMD": {"shares": 0, "short_calls": 100, "options": []}}

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        row = data[0]
        assert row["display_symbol"] == "AMD 2026-04-02 202.5 Call"
        assert row["market_price"] == 2.95
        assert row["market_value"] == -295.0
        assert row["unrealized_pnl"] == 180.0
        assert row["cost_basis"] == 4.75
        assert row["merged_sources"] == ["flex", "tws"]


def test_get_portfolio_holdings_coverage_with_ibkr_pascal_case_asset_class(client):
    """Regression test: IBKR CSV stores field as 'AssetClass' (PascalCase), not 'asset_class'.

    Verifies the fix for the bug where STK rows were not recognized because
    the coverage aggregation only checked snake_case field names.
    """
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        # Simulate real IBKR CSV data (PascalCase "AssetClass" field)
        mock_holdings = [
            # AMD: 200 shares, no short calls -> should be Uncovered
            {
                "symbol": "AMD",
                "AssetClass": "STK",
                "account_id": "U110638",
                "quantity": 200,
                "report_date": "2026-03-28"
            },
            # OLN: 100 shares, 1 short call -> should be Covered (100 == 100)
            {
                "symbol": "OLN",
                "AssetClass": "STK",
                "account_id": "U110638",
                "quantity": 100,
                "report_date": "2026-03-28"
            },
            {
                "symbol": "OLN   260417C00025000",
                "AssetClass": "OPT",
                "secType": "OPT",
                "account_id": "U110638",
                "quantity": -1,
                "underlying_symbol": "OLN",
                "multiplier": 100
            },
            # ERO: 300 shares, 2 short calls (200 equiv) -> should be Uncovered
            {
                "symbol": "ERO",
                "AssetClass": "STK",
                "account_id": "U110638",
                "quantity": 300,
                "report_date": "2026-03-28"
            },
            {
                "symbol": "ERO   260417C00025000",
                "AssetClass": "OPT",
                "secType": "OPT",
                "account_id": "U110638",
                "quantity": -1,
                "underlying_symbol": "ERO",
                "multiplier": 100
            },
            {
                "symbol": "ERO   260417C00030000",
                "AssetClass": "OPT",
                "secType": "OPT",
                "account_id": "U110638",
                "quantity": -1,
                "underlying_symbol": "ERO",
                "multiplier": 100
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        amd_stk = next(h for h in data if h["symbol"] == "AMD")
        oln_stk = next(h for h in data if h["symbol"] == "OLN")
        ero_stk = next(h for h in data if h["symbol"] == "ERO")

        # AMD: 200 shares, 0 short calls -> Uncovered
        assert amd_stk["coverage_status"] == "Uncovered"
        assert amd_stk["share_quantity_total"] == 200
        assert amd_stk["covered_shares"] == 0

        # OLN: 100 shares, 100 short call equiv -> Covered
        assert oln_stk["coverage_status"] == "Covered"
        assert oln_stk["coverage_mismatch"] is False
        assert oln_stk["share_quantity_total"] == 100
        assert oln_stk["covered_shares"] == 100

        # ERO: 300 shares, 200 short call equiv -> Uncovered
        assert ero_stk["coverage_status"] == "Uncovered"
        assert ero_stk["share_quantity_total"] == 300
        assert ero_stk["covered_shares"] == 200


def test_get_portfolio_holdings_adds_pending_cover_effect_for_uncovered_stock(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {"symbol": "AMD", "secType": "STK", "account_id": "U1", "quantity": 300, "market_price": 110.0},
            {"symbol": "AMD", "secType": "OPT", "account_id": "U1", "quantity": -1, "underlying_symbol": "AMD", "right": "C", "strike": 115.0, "expiry": "2026-04-18"},
        ]
        mock_orders = [
            {
                "order_key": "perm:1",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD",
                "underlying_symbol": "AMD",
                "secType": "OPT",
                "action": "SELL",
                "status": "Submitted",
                "remaining_quantity": 2,
                "multiplier": "100",
                "right": "C",
                "strike": 120.0,
                "last_trade_date": "20260425",
            }
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []
        mock_db.ibkr_orders.find.return_value = mock_orders

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        data = response.json()

        stock_row = next(h for h in data if h["security_type"] == "STK")
        option_row = next(h for h in data if h["security_type"] == "OPT")

        assert stock_row["coverage_status"] == "Uncovered"
        assert stock_row["pending_order_effect"] == "covering_uncovered"
        assert stock_row["coverage_status_if_filled"] == "Covered"
        assert stock_row["pending_cover_shares"] == 200.0
        assert stock_row["pending_cover_contracts"] == 2.0
        assert stock_row["uncovered_shares_now"] == 200.0
        assert option_row["pending_order_effect"] == "covering_uncovered"


def test_get_portfolio_holdings_adds_pending_buy_to_close_effect(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {"symbol": "AMD", "secType": "STK", "account_id": "U1", "quantity": 100, "market_price": 110.0},
            {"symbol": "AMD", "secType": "OPT", "account_id": "U1", "quantity": -1, "underlying_symbol": "AMD", "right": "C", "strike": 115.0, "expiry": "2026-04-18"},
        ]
        mock_orders = [
            {
                "order_key": "perm:2",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD",
                "underlying_symbol": "AMD",
                "secType": "OPT",
                "action": "BUY",
                "status": "Submitted",
                "remaining_quantity": 1,
                "multiplier": "100",
                "right": "C",
                "strike": 115.0,
                "last_trade_date": "20260418",
            }
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []
        mock_db.ibkr_orders.find.return_value = mock_orders

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        stock_row = next(h for h in response.json() if h["security_type"] == "STK")

        assert stock_row["coverage_status"] == "Covered"
        assert stock_row["pending_order_effect"] == "buying_to_close"
        assert stock_row["coverage_status_if_filled"] == "Uncovered"
        assert stock_row["pending_buy_to_close_contracts"] == 1.0


def test_get_portfolio_holdings_adds_pending_roll_effect(client):
    with patch("app.api.routes.MongoClient") as mock_mongo_cls:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_cls.return_value = mock_client
        mock_client.get_default_database.return_value = mock_db

        mock_holdings = [
            {"symbol": "AMD", "secType": "STK", "account_id": "U1", "quantity": 100, "market_price": 110.0},
            {"symbol": "AMD", "secType": "OPT", "account_id": "U1", "quantity": -1, "underlying_symbol": "AMD", "right": "C", "strike": 115.0, "expiry": "2026-04-18"},
        ]
        mock_orders = [
            {
                "order_key": "perm:3",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD",
                "underlying_symbol": "AMD",
                "secType": "OPT",
                "action": "BUY",
                "status": "Submitted",
                "remaining_quantity": 1,
                "multiplier": "100",
                "right": "C",
                "strike": 115.0,
                "last_trade_date": "20260418",
            },
            {
                "order_key": "perm:4",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD",
                "underlying_symbol": "AMD",
                "secType": "OPT",
                "action": "SELL",
                "status": "Submitted",
                "remaining_quantity": 1,
                "multiplier": "100",
                "right": "C",
                "strike": 120.0,
                "last_trade_date": "20260425",
            },
        ]

        mock_db.ibkr_holdings.find_one.return_value = {"snapshot_id": "test_snap"}
        mock_db.ibkr_holdings.find.return_value = mock_holdings
        mock_db.ibkr_dividends.aggregate.return_value = []
        mock_db.ibkr_orders.find.return_value = mock_orders

        response = client.get("/api/portfolio/holdings")
        assert response.status_code == 200
        stock_row = next(h for h in response.json() if h["security_type"] == "STK")

        assert stock_row["coverage_status"] == "Covered"
        assert stock_row["pending_order_effect"] == "rolling"
        assert stock_row["coverage_status_if_filled"] == "Covered"
        assert stock_row["pending_buy_to_close_contracts"] == 1.0
        assert stock_row["pending_cover_contracts"] == 1.0
        assert stock_row["pending_roll_contracts"] == 1.0
