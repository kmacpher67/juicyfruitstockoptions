from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.models import User


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = int(direction) < 0
        self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[: int(n)]
        return self

    def __iter__(self):
        return iter(self._docs)


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def create_index(self, *args, **kwargs):
        return "ok"

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find_one(self, query, projection=None, sort=None):
        matches = [doc for doc in self.docs if _matches(doc, query)]
        if sort:
            key, direction = sort[0]
            matches.sort(key=lambda d: d.get(key), reverse=int(direction) < 0)
        if not matches:
            return None
        return _project(matches[0], projection)

    def find(self, query=None, projection=None):
        query = query or {}
        return _FakeCursor([_project(doc, projection) for doc in self.docs if _matches(doc, query)])

    def update_one(self, query, update, upsert=False):
        for idx, doc in enumerate(self.docs):
            if _matches(doc, query):
                next_doc = dict(doc)
                next_doc.update(update.get("$set", {}))
                self.docs[idx] = next_doc
                return
        if upsert:
            next_doc = dict(query)
            next_doc.update(update.get("$set", {}))
            self.docs.append(next_doc)


def _matches(doc, query):
    for key, value in (query or {}).items():
        if doc.get(key) != value:
            return False
    return True


def _project(doc, projection):
    if not projection:
        return dict(doc)
    if projection == {"_id": 0}:
        return dict(doc)
    out = {}
    for key, include in projection.items():
        if key == "_id":
            continue
        if include and key in doc:
            out[key] = doc[key]
    return out


class _FakeDB:
    def __init__(self):
        self.juicy_fr_followup_reviews = _FakeCollection()


class _FakeMongoClient:
    def __init__(self):
        self.db = _FakeDB()

    def get_default_database(self, name=None):
        return self.db


@pytest.fixture
def fr_client(monkeypatch):
    fake_client = _FakeMongoClient()

    def _mock_mongo_client(*args, **kwargs):
        return fake_client

    monkeypatch.setattr("app.api.routes.MongoClient", _mock_mongo_client)

    async def mock_get_current_active_user():
        return User(username="testuser", role="admin", disabled=False)

    app.dependency_overrides[routes.get_current_active_user] = mock_get_current_active_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _ratio_spread_payload():
    return {
        "ticker": "msft",
        "trade_date": "2026-04-19",
        "strategy_type": "BULL_PUT_RATIO_SPREAD_1X2",
        "legs": [
            {
                "side": "LONG",
                "option_type": "PUT",
                "quantity": 1,
                "strike": 475.0,
                "expiration": "2026-05-15",
                "delta": -0.62,
                "moneyness": "ITM",
            },
            {
                "side": "SHORT",
                "option_type": "PUT",
                "quantity": 2,
                "strike": 460.0,
                "expiration": "2026-05-15",
                "delta": -0.32,
                "moneyness": "OTM",
            },
        ],
        "net_credit": 4.25,
        "notes": "Initial F-R entry",
    }


def _itm_substitution_payload():
    return {
        "ticker": "AAPL",
        "trade_date": "2026-04-19",
        "strategy_type": "DEEP_ITM_CALL_SUBSTITUTION_PMCC",
        "legs": [
            {
                "side": "LONG",
                "option_type": "CALL",
                "quantity": 1,
                "strike": 140.0,
                "expiration": "2026-10-16",
                "delta": 0.88,
                "moneyness": "ITM",
            },
            {
                "side": "SHORT",
                "option_type": "CALL",
                "quantity": 1,
                "strike": 175.0,
                "expiration": "2026-05-15",
                "delta": 0.28,
                "moneyness": "OTM",
            },
        ],
        "net_credit": 1.5,
    }


def test_create_fr_ratio_spread_persists_effective_entry_price(fr_client):
    res = fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())

    assert res.status_code == 200
    body = res.json()
    assert body["fr_id"].startswith("fr_")
    assert body["status"] == "F-R"
    assert body["review_state"] == "Active"
    assert body["ticker"] == "MSFT"
    assert body["effective_entry_price"] == pytest.approx(455.75)


def test_create_fr_rejects_invalid_ratio_spread_legs(fr_client):
    payload = _ratio_spread_payload()
    payload["legs"][0]["moneyness"] = "OTM"

    res = fr_client.post("/api/juicys/followup-review", json=payload)

    assert res.status_code == 422


def test_create_fr_itm_substitution_validates_delta_and_computes_effective_entry(fr_client):
    res = fr_client.post("/api/juicys/followup-review", json=_itm_substitution_payload())

    assert res.status_code == 200
    body = res.json()
    assert body["strategy_type"] == "DEEP_ITM_CALL_SUBSTITUTION_PMCC"
    assert body["effective_entry_price"] == pytest.approx(138.5)


def test_update_fr_review_state_transitions_allow_active_to_assigned_to_reviewed(fr_client):
    create_res = fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())
    fr_id = create_res.json()["fr_id"]

    assigned_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"review_state": "Assigned"},
    )
    assert assigned_res.status_code == 200
    assert assigned_res.json()["review_state"] == "Assigned"

    reviewed_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"review_state": "Reviewed"},
    )
    assert reviewed_res.status_code == 200
    assert reviewed_res.json()["review_state"] == "Reviewed"


def test_update_fr_rejects_invalid_review_state_transition(fr_client):
    create_res = fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())
    fr_id = create_res.json()["fr_id"]

    reviewed_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"review_state": "Reviewed"},
    )
    assert reviewed_res.status_code == 200

    invalid_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"review_state": "Active"},
    )
    assert invalid_res.status_code == 400
    assert "Invalid review_state transition" in invalid_res.json()["detail"]


def test_update_fr_mtm_sync_sets_timestamp_when_underlying_price_updates(fr_client):
    create_res = fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())
    fr_id = create_res.json()["fr_id"]

    update_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"underlying_last_price": 468.25},
    )
    assert update_res.status_code == 200
    body = update_res.json()
    assert body["underlying_last_price"] == 468.25
    assert body["last_mtm_sync_at"] is not None
    datetime.fromisoformat(body["last_mtm_sync_at"].replace("Z", "+00:00"))


def test_update_fr_recomputes_effective_entry_when_net_credit_changes(fr_client):
    create_res = fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())
    fr_id = create_res.json()["fr_id"]

    update_res = fr_client.patch(
        f"/api/juicys/followup-review/{fr_id}",
        json={"net_credit": 6.0},
    )

    assert update_res.status_code == 200
    assert update_res.json()["effective_entry_price"] == pytest.approx(454.0)


def test_list_fr_items_filters_by_status_and_strategy_type(fr_client):
    fr_client.post("/api/juicys/followup-review", json=_ratio_spread_payload())
    fr_client.post("/api/juicys/followup-review", json=_itm_substitution_payload())

    ratio_res = fr_client.get(
        "/api/juicys/followup-review",
        params={"status": "F-R", "strategy_type": "BULL_PUT_RATIO_SPREAD_1X2"},
    )
    assert ratio_res.status_code == 200
    ratio_rows = ratio_res.json()["rows"]
    assert len(ratio_rows) == 1
    assert ratio_rows[0]["strategy_type"] == "BULL_PUT_RATIO_SPREAD_1X2"

    itm_res = fr_client.get(
        "/api/juicys/followup-review",
        params={"status": "F-R", "strategy_type": "DEEP_ITM_CALL_SUBSTITUTION_PMCC"},
    )
    assert itm_res.status_code == 200
    itm_rows = itm_res.json()["rows"]
    assert len(itm_rows) == 1
    assert itm_rows[0]["strategy_type"] == "DEEP_ITM_CALL_SUBSTITUTION_PMCC"
