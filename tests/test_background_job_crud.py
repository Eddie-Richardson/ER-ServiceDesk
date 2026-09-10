# ER-ServiceDesk/tests/test_background_job_crud.py
"""
Covers BackgroundJobCRUD's real database-level filters (job_type,
status) -- every other existing test only ever fetches unfiltered and
checks the result in Python, never exercising these real SQL filter
conditions directly.
"""

from app.crud.background_job import crud_background_job
from app.schemas.background_job import BackgroundJobCreate


def test_get_multi_filters_by_job_type(db):
    crud_background_job.create(db, BackgroundJobCreate(job_type="poll_inbound_email", status="completed"))
    crud_background_job.create(db, BackgroundJobCreate(job_type="archive_inactive_customers", status="completed"))

    result = crud_background_job.get_multi(db, job_type="poll_inbound_email")

    assert len(result) == 1
    assert result[0].job_type == "poll_inbound_email"


def test_get_multi_filters_by_status(db):
    crud_background_job.create(db, BackgroundJobCreate(job_type="poll_inbound_email", status="completed"))
    crud_background_job.create(db, BackgroundJobCreate(job_type="poll_inbound_email", status="failed"))

    result = crud_background_job.get_multi(db, status="failed")

    assert len(result) == 1
    assert result[0].status == "failed"


def test_background_jobs_is_read_only(client, agent_headers):
    """BackgroundJob is a deliberately immutable, internally-generated record (created only by worker tasks, via start()/complete()/fail()) -- no create route exists via the API, only listing."""
    list_resp = client.get("/background_jobs/", headers=agent_headers)
    assert list_resp.status_code == 200
    create_resp = client.post("/background_jobs/", json={"job_type": "send_email", "status": "queued"}, headers=agent_headers)
    assert create_resp.status_code == 405
