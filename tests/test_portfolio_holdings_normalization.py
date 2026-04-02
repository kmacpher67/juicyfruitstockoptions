from unittest.mock import MagicMock

from app.api.routes import _load_portfolio_holdings_rows, _merge_portfolio_rows, _normalize_portfolio_row, _portfolio_row_key


def test_normalize_portfolio_row_maps_live_tws_option_shape():
    row = _normalize_portfolio_row(
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
        }
    )

    assert row["security_type"] == "OPT"
    assert row["account_id"] == "U110638"
    assert row["quantity"] == -1
    assert row["cost_basis"] == 5.25
    assert row["display_symbol"] == "AMD 2026-04-02 202.5 Call"
    assert row["percent_of_nav"] is None


def test_normalize_portfolio_row_keeps_missing_live_values_null_and_percent_fractional():
    row = _normalize_portfolio_row(
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
    )

    assert row["security_type"] == "STK"
    assert row["display_symbol"] == "MSFT"
    assert row["percent_of_nav"] == 0.125
    assert row["market_price"] is None
    assert row["market_value"] is None
    assert row["cost_basis"] is None
    assert row["unrealized_pnl"] is None


def test_portfolio_row_key_matches_flex_and_tws_option_shapes():
    flex_row = _normalize_portfolio_row(
        {
            "symbol": "AMD  260402C00202500",
            "asset_class": "OPT",
            "account_id": "U110638",
            "quantity": -1,
            "expiry": "2026-04-02",
            "right": "C",
            "strike": 202.5,
            "source": "flex",
        }
    )
    tws_row = _normalize_portfolio_row(
        {
            "symbol": "AMD",
            "local_symbol": "AMD   260402C00202500",
            "secType": "OPT",
            "account": "U110638",
            "position": -1,
            "last_trade_date": "20260402",
            "right": "C",
            "strike": 202.5,
            "source": "tws",
        }
    )

    assert _portfolio_row_key(flex_row) == _portfolio_row_key(tws_row)


def test_merge_portfolio_rows_prefers_live_values_without_losing_flex_fields():
    flex_row = _normalize_portfolio_row(
        {
            "symbol": "AMD  260402C00202500",
            "asset_class": "OPT",
            "account_id": "U110638",
            "quantity": -1,
            "cost_basis": 4.75,
            "market_price": 3.2,
            "market_value": -320.0,
            "unrealized_pnl": 155.0,
            "expiry": "2026-04-02",
            "right": "C",
            "strike": 202.5,
            "source": "flex",
        }
    )
    tws_row = _normalize_portfolio_row(
        {
            "symbol": "AMD",
            "local_symbol": "AMD   260402C00202500",
            "secType": "OPT",
            "account": "U110638",
            "position": -1,
            "market_price": 2.95,
            "market_value": -295.0,
            "unrealized_pnl": 180.0,
            "last_tws_update": "2026-03-31T14:35:00Z",
            "last_trade_date": "20260402",
            "right": "C",
            "strike": 202.5,
            "source": "tws",
        }
    )

    merged = _merge_portfolio_rows(flex_row, tws_row)

    assert merged["market_price"] == 2.95
    assert merged["market_value"] == -295.0
    assert merged["unrealized_pnl"] == 180.0
    assert merged["cost_basis"] == 4.75
    assert merged["display_symbol"] == "AMD 2026-04-02 202.5 Call"
    assert merged["merged_sources"] == ["flex", "tws"]


def test_load_portfolio_holdings_rows_merges_latest_flex_and_tws_snapshots():
    mock_db = MagicMock()

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

    rows = _load_portfolio_holdings_rows(mock_db)

    assert len(rows) == 1
    row = rows[0]
    assert row["display_symbol"] == "AMD 2026-04-02 202.5 Call"
    assert row["market_price"] == 2.95
    assert row["market_value"] == -295.0
    assert row["unrealized_pnl"] == 180.0
    assert row["cost_basis"] == 4.75
    assert row["merged_sources"] == ["flex", "tws"]
