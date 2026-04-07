from app.api import routes
from app.models import FrontendLogPayload, User


def test_frontend_log_ingest_endpoint_accepts_structured_payload():
    payload = FrontendLogPayload(
        **{
            "level": "error",
            "source": "frontend",
            "boundary": "dashboard",
            "message": "render failed",
            "stack": "Error: render failed",
            "componentStack": "\n in Dashboard",
            "timestamp": "2026-04-07T12:00:00Z",
            "path": "/dashboard",
        }
    )
    user = User(username="testuser", role="admin", disabled=False)
    response = routes.ingest_frontend_log(payload, user)
    assert response == {"status": "logged"}
