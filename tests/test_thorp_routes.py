"""
Route-level tests for GET /api/thorp/{symbol}:
  - 401 without valid token
  - Symbol sanitization (reject invalid chars)
  - Full response shape (all required fields)
  - INSUFFICIENT_DATA full-response path
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

import app.auth.dependencies
from app.main import app as fastapi_app
from app.models import User
from app.models.thorp import ThorpAuditResponse, ThorpDecision, ThorpPoint, ThorpStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client():
    """TestClient with auth bypass."""
    async def _mock_user():
        return User(
            username="testuser",
            email="test@example.com",
            role="admin",
            hashed_password="pw",
            disabled=False,
        )

    fastapi_app.dependency_overrides[app.auth.dependencies.get_current_active_user] = _mock_user
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def unauth_client():
    """TestClient with no auth override."""
    fastapi_app.dependency_overrides.clear()
    with TestClient(fastapi_app) as c:
        yield c


def _full_response(symbol: str = "AMD") -> ThorpAuditResponse:
    points = [
        ThorpPoint(id="edge_audit", label="Edge Audit", status=ThorpStatus.EDGE, key_metric="E=8%", detail="ok"),
        ThorpPoint(id="position_sizing", label="Kelly Position Sizing", status=ThorpStatus.EDGE, key_metric="12%", detail="ok"),
        ThorpPoint(id="inefficiency_map", label="Inefficiency Map", status=ThorpStatus.EDGE, key_metric="skew=1.1", detail="ok"),
        ThorpPoint(id="ruin_check", label="Ruin Check (-25% Sim)", status=ThorpStatus.EDGE, key_metric="-2% NLV", detail="ok"),
        ThorpPoint(id="fraud_scan", label="Fraud Scan", status=ThorpStatus.EDGE, key_metric="1.2x", detail="ok"),
        ThorpPoint(id="compounding_review", label="Compounding Review", status=ThorpStatus.EDGE, key_metric="20% ann", detail="ok"),
        ThorpPoint(id="adaptability_check", label="Adaptability Check", status=ThorpStatus.EDGE, key_metric="+0.5%", detail="ok"),
        ThorpPoint(id="independence_test", label="Independence Test", status=ThorpStatus.EDGE, key_metric="0.55", detail="ok"),
        ThorpPoint(id="circle_of_competence", label="Circle of Competence", status=ThorpStatus.EDGE, key_metric="70% n=10", detail="ok"),
        ThorpPoint(id="thorp_decision", label="Thorp Decision", status=ThorpStatus.EDGE, key_metric="3 actions", detail="ok"),
    ]
    decisions = [
        ThorpDecision(rank=1, action="Increase", edge="edge ok", risk="size risk", first_step="add contracts"),
        ThorpDecision(rank=2, action="Monitor", edge="stable", risk="none", first_step="check next expiry"),
        ThorpDecision(rank=3, action="Continue wheel", edge="compounding", risk="decay", first_step="review next cycle"),
    ]
    return ThorpAuditResponse(
        symbol=symbol,
        as_of=datetime.now(tz=timezone.utc),
        points=points,
        thorp_decision=decisions,
        data_completeness=1.0,
    )


def _insufficient_response(symbol: str = "EMPTY") -> ThorpAuditResponse:
    points = [
        ThorpPoint(id=pid, label=pid, status=ThorpStatus.INSUFFICIENT_DATA, key_metric="N/A", detail="no data")
        for pid in [
            "edge_audit", "position_sizing", "inefficiency_map", "ruin_check",
            "fraud_scan", "compounding_review", "adaptability_check",
            "independence_test", "circle_of_competence", "thorp_decision",
        ]
    ]
    decisions = [
        ThorpDecision(rank=1, action="Hold — no data", edge="insufficient", risk="unknown", first_step="Run Live Analysis"),
        ThorpDecision(rank=2, action="Monitor", edge="N/A", risk="N/A", first_step="Refresh data"),
        ThorpDecision(rank=3, action="Continue", edge="N/A", risk="N/A", first_step="Recheck after data refresh"),
    ]
    return ThorpAuditResponse(
        symbol=symbol,
        as_of=datetime.now(tz=timezone.utc),
        points=points,
        thorp_decision=decisions,
        data_completeness=0.0,
    )


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestThorpRouteAuth:
    def test_401_without_token(self, unauth_client):
        response = unauth_client.get("/api/thorp/AMD")
        assert response.status_code == 401

    @patch("app.api.routes.MongoClient")
    @patch("app.api.routes.ThorpService", create=True)
    def test_200_with_valid_token(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        with patch("app.services.thorp_service.ThorpService", mock_svc_cls):
            response = auth_client.get("/api/thorp/AMD")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Symbol sanitization
# ---------------------------------------------------------------------------

class TestThorpSymbolSanitization:
    @patch("app.api.routes.MongoClient")
    def test_rejects_script_injection(self, mock_mongo, auth_client):
        response = auth_client.get("/api/thorp/<script>alert(1)</script>")
        assert response.status_code in (400, 404, 422)

    @patch("app.api.routes.MongoClient")
    def test_rejects_semicolon(self, mock_mongo, auth_client):
        response = auth_client.get("/api/thorp/AMD;DROP")
        assert response.status_code in (400, 404, 422)

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_accepts_valid_symbol(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/AMD")
        assert response.status_code == 200

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_accepts_dot_slash_hyphen(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("BRK.B"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/BRK.B")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Full response shape
# ---------------------------------------------------------------------------

class TestThorpResponseShape:
    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_required_top_level_fields(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/AMD")
        assert response.status_code == 200
        data = response.json()
        assert "symbol" in data
        assert "as_of" in data
        assert "points" in data
        assert "thorp_decision" in data
        assert "data_completeness" in data

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_points_have_required_fields(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/AMD")
        data = response.json()
        for pt in data["points"]:
            assert "id" in pt
            assert "label" in pt
            assert "status" in pt
            assert "key_metric" in pt
            assert "detail" in pt

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_thorp_decision_has_required_fields(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/AMD")
        data = response.json()
        for d in data["thorp_decision"]:
            assert "rank" in d
            assert "action" in d
            assert "edge" in d
            assert "risk" in d
            assert "first_step" in d

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_data_completeness_range(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/AMD")
        data = response.json()
        assert 0.0 <= data["data_completeness"] <= 1.0

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_symbol_uppercased_in_response(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_full_response("AMD"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/amd")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AMD"


# ---------------------------------------------------------------------------
# INSUFFICIENT_DATA full-response path
# ---------------------------------------------------------------------------

class TestThorpInsufficientData:
    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_insufficient_data_completeness_zero(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_insufficient_response("EMPTY"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/EMPTY")
        assert response.status_code == 200
        data = response.json()
        assert data["data_completeness"] == 0.0

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_insufficient_data_all_points_present(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_insufficient_response("EMPTY"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/EMPTY")
        data = response.json()
        assert len(data["points"]) == 10
        statuses = {p["status"] for p in data["points"]}
        assert "INSUFFICIENT_DATA" in statuses

    @patch("app.api.routes.MongoClient")
    @patch("app.services.thorp_service.ThorpService")
    def test_decisions_still_present_when_no_data(self, mock_svc_cls, mock_mongo, auth_client):
        mock_svc = MagicMock()
        mock_svc.compute = AsyncMock(return_value=_insufficient_response("EMPTY"))
        mock_svc_cls.return_value = mock_svc
        response = auth_client.get("/api/thorp/EMPTY")
        data = response.json()
        assert len(data["thorp_decision"]) == 3
