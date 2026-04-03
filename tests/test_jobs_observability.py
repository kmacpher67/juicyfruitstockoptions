import pytest

from app.api import routes
from app.jobs import (
    JobStatus,
    create_job,
    current_jobs,
    get_latest_job,
    list_jobs,
)
from app.models import User


@pytest.fixture(autouse=True)
def _reset_jobs():
    current_jobs.clear()
    yield
    current_jobs.clear()


def test_create_job_supports_type_and_latest_lookup():
    j1 = create_job(job_type="stock_live_comparison", name="stock-live-comparison")
    j2 = create_job(job_type="ibkr_sync", name="ibkr-sync")

    assert j1.job_type == "stock_live_comparison"
    assert j1.status == JobStatus.QUEUED
    assert len(list_jobs(job_type="stock_live_comparison")) == 1
    latest = get_latest_job(job_type="ibkr_sync")
    assert latest and latest.id == j2.id


def test_background_job_wrapper_marks_exception_as_failed():
    job = create_job(job_type="stock_live_comparison", name="stock-live-comparison")

    def boom():
        raise RuntimeError("boom")

    routes.background_job_wrapper(job.id, boom)
    updated = current_jobs[job.id]
    assert updated.status == JobStatus.FAILED
    assert updated.message == "failed"
    assert "boom" in (updated.error or "")


def test_latest_stock_live_job_endpoint():
    created = create_job(job_type="stock_live_comparison", name="stock-live-comparison")
    result = routes.get_latest_stock_live_job(
        current_user=User(username="testuser", role="admin", disabled=False)
    )
    assert result.id == created.id
    assert result.job_type == "stock_live_comparison"
