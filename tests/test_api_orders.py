import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import routes
from app.models import IBKRConfig, User


def test_get_open_orders_requires_portfolio_access():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.get_open_orders(current_user=User(username="u", role="basic", disabled=False)))
    assert exc.value.status_code == 403
    assert "Portfolio access required" in exc.value.detail


def test_get_open_orders_returns_active_rows_with_market_context():
    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db

        mock_db.ibkr_orders.find.return_value = [
            {
                "order_key": "perm:9001",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD   260417C00120000",
                "local_symbol": "AMD   260417C00120000",
                "secType": "OPT",
                "right": "C",
                "strike": 120.0,
                "status": "Submitted",
                "action": "SELL",
                "remaining_quantity": 2,
                "total_quantity": 2,
                "filled_quantity": 0,
                "order_type": "LMT",
                "limit_price": 1.25,
                "last_tws_update": "2026-04-02T12:15:00+00:00",
            },
            {
                "order_key": "perm:9002",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "MSFT",
                "secType": "STK",
                "status": "Filled",
                "action": "BUY",
                "remaining_quantity": 0,
                "total_quantity": 10,
                "filled_quantity": 10,
            },
        ]
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "Current Price": 188.23,
            "1D % Change": 1.42,
            "Call/Put Skew": 2.11,
            "TSMOM_60": 0.33,
        }

        payload = asyncio.run(
            routes.get_open_orders(current_user=User(username="u", role="admin", disabled=False))
        )
    assert len(payload) == 1
    assert payload[0]["underlying_ticker"] == "AMD"
    assert payload[0]["is_active"] is True
    assert payload[0]["last_price"] == 188.23
    assert payload[0]["day_change_pct"] == 1.42
    assert payload[0]["call_put_skew"] == 2.11


def test_update_ibkr_config_persists_orders_query_id():
    admin = User(username="admin", role="admin", disabled=False)

    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db

        routes.update_ibkr_config(
            IBKRConfig(query_id_orders="ORDERS_QUERY_123"),
            current_user=admin,
        )

    args, kwargs = mock_db.system_config.update_one.call_args
    assert args[0] == {"_id": "ibkr_config"}
    assert args[1]["$set"]["query_id_orders"] == "ORDERS_QUERY_123"
    assert kwargs.get("upsert") is True


def test_get_open_orders_active_only_false_includes_filled_rows():
    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db

        mock_db.ibkr_orders.find.return_value = [
            {
                "order_key": "perm:1",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AAPL",
                "secType": "STK",
                "status": "Filled",
                "action": "BUY",
                "remaining_quantity": 0,
                "total_quantity": 10,
                "filled_quantity": 10,
            }
        ]
        mock_db.stock_data.find_one.return_value = {"Ticker": "AAPL", "Current Price": 200.0}

        payload = asyncio.run(
            routes.get_open_orders(
                current_user=User(username="u", role="portfolio", disabled=False),
                active_only=False,
            )
        )

    assert len(payload) == 1
    assert payload[0]["status"] == "Filled"
    assert payload[0]["is_active"] is False
    assert payload[0]["last_price"] == 200.0


def test_get_order_live_status_requires_portfolio_access():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.get_order_live_status(current_user=User(username="u", role="basic", disabled=False)))
    assert exc.value.status_code == 403
    assert "Portfolio access required" in exc.value.detail


def test_get_order_live_status_returns_tws_payload():
    fake_service = MagicMock()
    fake_service.get_live_status.return_value = {
        "connected": True,
        "connection_state": "connected",
        "last_order_update": "2026-04-02T14:00:00+00:00",
        "order_count": 4,
    }

    with patch("app.api.routes.get_ibkr_tws_service", return_value=fake_service):
        payload = asyncio.run(
            routes.get_order_live_status(current_user=User(username="u", role="admin", disabled=False))
        )

    assert payload["connected"] is True
    assert payload["connection_state"] == "connected"
    assert payload["order_count"] == 4


def test_get_open_orders_hides_inactive_status_rows_by_default():
    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db
        mock_db.ibkr_orders.find.return_value = [
            {
                "order_key": "perm:77",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AAPL",
                "secType": "STK",
                "status": "Inactive",
                "action": "BUY",
                "remaining_quantity": 0,
                "total_quantity": 10,
                "filled_quantity": 10,
            }
        ]
        mock_db.stock_data.find_one.return_value = {"Ticker": "AAPL", "Current Price": 200.0}

        payload = asyncio.run(
            routes.get_open_orders(current_user=User(username="u", role="admin", disabled=False))
        )

    assert payload == []


def test_normalize_order_row_infers_option_contract_fields_from_occ_symbol():
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U1",
            "symbol": "AMD   260417C00120000",
            "action": "SLD",
            "status": "Submitted",
            "total_quantity": 2,
            "filled_quantity": 0,
            "source": "tws_open_order",
        }
    )

    assert normalized["security_type"] == "OPT"
    assert normalized["underlying_symbol"] == "AMD"
    assert normalized["display_symbol"].startswith("AMD ")
    assert normalized["display_symbol"].endswith("120 Call")
    assert normalized["action"] == "SELL"
    assert normalized["remaining_quantity"] == 2.0
    assert normalized["is_active"] is True


def test_normalize_order_row_handles_stock_orders_and_remaining_qty_fallback():
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U2",
            "symbol": "AAPL",
            "secType": "STK",
            "action": "BOT",
            "status": "PreSubmitted",
            "total_quantity": 10,
            "filled_quantity": 4,
            "source": "tws_open_order",
        }
    )

    assert normalized["security_type"] == "STK"
    assert normalized["display_symbol"] == "AAPL"
    assert normalized["action"] == "BUY"
    assert normalized["remaining_quantity"] == 6.0
    assert normalized["is_active"] is True


def test_get_open_orders_retains_roll_like_paired_rows_for_same_underlying():
    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db
        mock_db.ibkr_orders.find.return_value = [
            {
                "order_key": "perm:7001",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD   260417C00120000",
                "action": "BUY",
                "status": "Submitted",
                "remaining_quantity": 1,
                "total_quantity": 1,
            },
            {
                "order_key": "perm:7002",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD   260516C00130000",
                "action": "SELL",
                "status": "Submitted",
                "remaining_quantity": 1,
                "total_quantity": 1,
            },
        ]
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "Current Price": 188.23,
        }

        payload = asyncio.run(
            routes.get_open_orders(current_user=User(username="u", role="admin", disabled=False))
        )

    assert len(payload) == 2
    display_symbols = {row["display_symbol"] for row in payload}
    assert any(symbol.endswith("120 Call") for symbol in display_symbols)
    assert any(symbol.endswith("130 Call") for symbol in display_symbols)
    assert {row["action"] for row in payload} == {"BUY", "SELL"}
    assert all(row["underlying_ticker"] == "AMD" for row in payload)


def test_normalize_order_row_handles_bag_combo_parent_shape():
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U3",
            "symbol": "AAPL",
            "secType": "BAG",
            "local_symbol": "AAPL COMBO",
            "action": "SELL",
            "status": "Submitted",
            "total_quantity": 1,
            "filled_quantity": 0,
            "source": "tws_open_order",
            "comboLegs": [
                {"action": "BUY", "ratio": 1, "conId": 111},
                {"action": "SELL", "ratio": 1, "conId": 222},
            ],
        }
    )

    assert normalized["security_type"] == "BAG"
    assert normalized["display_symbol"] == "AAPL"
    assert normalized["action"] == "SELL"
    assert normalized["remaining_quantity"] == 1.0
    assert normalized["is_active"] is True


# ---------------------------------------------------------------------------
# ibkr-orders-012 — BAG leg decomposition: API response tests
# ---------------------------------------------------------------------------


def test_normalize_order_row_bag_preserves_combo_legs_in_response():
    """BAG orders must include comboLegs in their normalized output."""
    legs = [
        {"action": "BUY", "ratio": 1, "conid": 111, "exchange": "CBOE"},
        {"action": "SELL", "ratio": 1, "conid": 222, "exchange": "CBOE"},
    ]
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U4",
            "symbol": "AMD",
            "secType": "BAG",
            "action": "SELL",
            "status": "Submitted",
            "total_quantity": 1,
            "filled_quantity": 0,
            "source": "tws_open_order",
            "comboLegs": legs,
        }
    )

    assert normalized["is_bag"] is True
    assert isinstance(normalized["comboLegs"], list)
    assert len(normalized["comboLegs"]) == 2


def test_normalize_order_row_bag_2_leg_roll_has_buy_and_sell_actions():
    """A 2-leg roll BAG order must have exactly one BUY and one SELL leg."""
    legs = [
        {"action": "BUY", "ratio": 1, "conid": 333},
        {"action": "SELL", "ratio": 1, "conid": 444},
    ]
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U5",
            "symbol": "MSFT",
            "secType": "BAG",
            "action": "SELL",
            "status": "PreSubmitted",
            "total_quantity": 2,
            "filled_quantity": 0,
            "source": "tws_open_order",
            "comboLegs": legs,
        }
    )

    combo_legs = normalized["comboLegs"]
    assert len(combo_legs) == 2
    actions = {leg["action"] for leg in combo_legs}
    assert actions == {"BUY", "SELL"}
    for leg in combo_legs:
        assert "action" in leg
        assert "ratio" in leg


def test_normalize_order_row_non_bag_has_no_combo_legs():
    """Non-BAG orders must not have a non-None comboLegs field."""
    normalized = routes._normalize_order_row(  # pylint: disable=protected-access
        {
            "account_id": "U6",
            "symbol": "AAPL",
            "secType": "STK",
            "action": "BUY",
            "status": "Submitted",
            "total_quantity": 10,
            "filled_quantity": 0,
            "source": "tws_open_order",
        }
    )

    assert normalized.get("comboLegs") is None
    assert normalized.get("is_bag") is False


def test_get_open_orders_bag_rows_include_combo_legs_in_api_response():
    """The /orders/open endpoint must return comboLegs for BAG orders."""
    with patch("app.api.routes.MongoClient") as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.get_default_database.return_value = mock_db

        mock_db.ibkr_orders.find.return_value = [
            {
                "order_key": "perm:8001",
                "source": "tws_open_order",
                "account_id": "U1",
                "symbol": "AMD",
                "secType": "BAG",
                "action": "SELL",
                "status": "Submitted",
                "remaining_quantity": 1,
                "total_quantity": 1,
                "filled_quantity": 0,
                "comboLegs": [
                    {"action": "BUY", "ratio": 1, "conid": 555},
                    {"action": "SELL", "ratio": 1, "conid": 666},
                ],
            },
        ]
        mock_db.stock_data.find_one.return_value = {
            "Ticker": "AMD",
            "Current Price": 170.00,
        }

        payload = asyncio.run(
            routes.get_open_orders(
                current_user=User(username="u", role="admin", disabled=False)
            )
        )

    assert len(payload) == 1
    row = payload[0]
    assert row["is_bag"] is True
    assert isinstance(row["comboLegs"], list)
    assert len(row["comboLegs"]) == 2
    leg_actions = {leg["action"] for leg in row["comboLegs"]}
    assert "BUY" in leg_actions
    assert "SELL" in leg_actions
