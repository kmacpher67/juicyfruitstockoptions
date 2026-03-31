from types import SimpleNamespace
from unittest.mock import MagicMock

import app.scheduler.jobs as jobs


class FakeTwsService:
    def __init__(self, *, connected=True, positions=None, account_values=None, executions=None):
        self._connected = connected
        self._positions = positions or []
        self._account_values = account_values or {}
        self._executions = executions or []
        self.app = SimpleNamespace(account_values=self._account_values)
        self.refresh_calls = []
        self.upsert_calls = []

    def is_connected(self):
        return self._connected

    def ensure_connected(self):
        return self._connected

    def get_positions(self):
        return list(self._positions)

    def get_account_values(self, account):
        return {
            key_name: payload
            for (account_name, key_name), payload in self._account_values.items()
            if account_name == account
        }

    def refresh_executions(self, account=None, req_id=9001):
        self.refresh_calls.append((account, req_id))
        return self._connected

    def upsert_executions_to_db(self, db=None, account=None):
        self.upsert_calls.append((db, account))
        return len(self._executions)

    def get_live_status(self):
        return {
            "connection_state": "connected" if self._connected else "disconnected",
            "socket_connectable": self._connected,
            "handshake_attempted": self._connected,
            "managed_accounts": [],
            "last_error": None,
            "execution_count": len(self._executions),
            "last_execution_update": "2026-03-31T12:15:00+00:00" if self._executions else None,
        }


def test_run_tws_position_sync_upserts_live_snapshot(monkeypatch):
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_default_database.return_value = mock_db
    monkeypatch.setattr(jobs, "MongoClient", MagicMock(return_value=mock_client))
    monkeypatch.setattr(jobs.settings, "IBKR_TWS_ENABLED", True)
    monkeypatch.setattr(
        jobs,
        "get_ibkr_tws_service",
        lambda: FakeTwsService(
            positions=[
                {
                    "account": "DU123456",
                    "symbol": "AAPL",
                    "sec_type": "STK",
                    "position": 10,
                    "avg_cost": 150.25,
                }
            ]
        ),
    )

    jobs.run_tws_position_sync()

    assert mock_db.ibkr_holdings.update_one.call_count == 1
    args, kwargs = mock_db.ibkr_holdings.update_one.call_args
    assert args[0]["account_id"] == "DU123456"
    assert args[0]["symbol"] == "AAPL"
    assert args[0]["secType"] == "STK"
    assert args[0]["source"] == "tws"
    stored_doc = args[1]["$set"]
    assert stored_doc["quantity"] == 10
    assert stored_doc["source"] == "tws"
    assert "snapshot_id" in stored_doc
    assert kwargs["upsert"] is True


def test_run_tws_nav_snapshot_inserts_account_values(monkeypatch):
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_default_database.return_value = mock_db
    monkeypatch.setattr(jobs, "MongoClient", MagicMock(return_value=mock_client))
    monkeypatch.setattr(jobs.settings, "IBKR_TWS_ENABLED", True)
    monkeypatch.setattr(
        jobs,
        "get_ibkr_tws_service",
        lambda: FakeTwsService(
            positions=[{"account": "DU123456", "symbol": "AAPL", "sec_type": "STK"}],
            account_values={
                ("DU123456", "NetLiquidation"): {"value": "25000.50"},
                ("DU123456", "UnrealizedPnL"): {"value": "125.25"},
                ("DU123456", "RealizedPnL"): {"value": "10.75"},
            },
        ),
    )

    jobs.run_tws_nav_snapshot()

    assert mock_db.ibkr_nav_history.insert_one.call_count == 1
    stored_doc = mock_db.ibkr_nav_history.insert_one.call_args[0][0]
    assert stored_doc["account_id"] == "DU123456"
    assert stored_doc["source"] == "tws"
    assert stored_doc["ending_value"] == 25000.50
    assert stored_doc["total_nav"] == 25000.50
    assert stored_doc["unrealized_pnl"] == 125.25
    assert stored_doc["realized_pnl"] == 10.75


def test_tag_existing_flex_sync_sources_updates_missing_source_docs(monkeypatch):
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_default_database.return_value = mock_db
    monkeypatch.setattr(jobs, "MongoClient", MagicMock(return_value=mock_client))

    jobs.tag_existing_flex_sync_sources()

    mock_db.ibkr_holdings.update_many.assert_called_once_with(
        {"source": {"$exists": False}},
        {"$set": {"source": "flex"}},
    )
    mock_db.ibkr_nav_history.update_many.assert_called_once_with(
        {"source": {"$exists": False}},
        {"$set": {"source": "flex"}},
    )


def test_run_tws_execution_sync_requests_and_upserts_live_executions(monkeypatch):
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_default_database.return_value = mock_db
    monkeypatch.setattr(jobs, "MongoClient", MagicMock(return_value=mock_client))
    monkeypatch.setattr(jobs.settings, "IBKR_TWS_ENABLED", True)
    fake_service = FakeTwsService(
        positions=[{"account": "DU123456", "symbol": "AAPL", "sec_type": "STK"}],
        account_values={("DU123456", "NetLiquidation"): {"value": "25000.50"}},
        executions=[{"exec_id": "abc123"}],
    )
    monkeypatch.setattr(jobs, "get_ibkr_tws_service", lambda: fake_service)

    jobs.run_tws_execution_sync()

    assert fake_service.refresh_calls == [("DU123456", 9100)]
    assert len(fake_service.upsert_calls) == 1
    assert fake_service.upsert_calls[0][0] is mock_db
