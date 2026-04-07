from dataclasses import dataclass

from fastapi import BackgroundTasks

from app.api.routes import User, run_stock_live_comparison_endpoint


@dataclass
class DummyJob:
    id: str


def test_run_endpoint_queues_single_background_task(monkeypatch):
    monkeypatch.setattr("app.api.routes.create_job", lambda *args, **kwargs: DummyJob(id="job-123"))
    background_tasks = BackgroundTasks()

    response = run_stock_live_comparison_endpoint(
        background_tasks=background_tasks,
        current_user=User(username="testuser", role="admin"),
    )

    assert response == {"job_id": "job-123", "status": "queued"}
    assert len(background_tasks.tasks) == 1


def test_run_endpoint_background_task_uses_manual_trigger(monkeypatch):
    monkeypatch.setattr("app.api.routes.create_job", lambda *args, **kwargs: DummyJob(id="job-456"))

    called = {}

    def fake_run_stock_live_comparison_with_optional_sharding(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return {"status": "success"}

    monkeypatch.setattr(
        "app.api.routes.run_stock_live_comparison_with_optional_sharding",
        fake_run_stock_live_comparison_with_optional_sharding,
    )

    background_tasks = BackgroundTasks()
    run_stock_live_comparison_endpoint(
        background_tasks=background_tasks,
        current_user=User(username="testuser", role="admin"),
    )

    # Execute queued task explicitly.
    task = background_tasks.tasks[0]
    task.func(*task.args, **task.kwargs)

    assert called["args"] == ()
    assert called["kwargs"] == {"trigger": "manual"}
