# ER-ServiceDesk/app/services/background_job_service.py
"""
Business logic for tracking a background task's real lifecycle --
running, completed, or failed -- as it actually executes.

start()/complete()/fail() are the real entry points every task in
app/workers/tasks.py calls around its own work, wrapped in a
try/except so a task's own failure still gets recorded rather than
silently leaving a job stuck showing "running" forever.
"""

from sqlalchemy.orm import Session
from app.crud.background_job import crud_background_job
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobService:
    """Read access to job history, plus the start/complete/fail lifecycle helpers tasks call around their own work."""

    def get(self, db: Session, id: int):
        return crud_background_job.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200, job_type: str | None = None, status: str | None = None):
        return crud_background_job.get_multi(db, skip, limit, job_type, status)

    def start(self, db: Session, job_type: str, payload: str | None = None):
        """
        Records a job actually starting -- call this right when a
        task's real work begins, not when it's merely enqueued (RQ
        itself already tracks the queued state; this table exists to
        give a persistent, queryable history of what actually ran,
        which RQ's own Redis-backed job data doesn't provide long-term).

        Args:
            job_type: The kind of job, e.g. "poll_inbound_email".

        Returns:
            The newly created BackgroundJob instance, with status
            "running". Pass its .id to complete() or fail() when the
            work finishes.
        """
        return crud_background_job.create(db, BackgroundJobCreate(
            job_type=job_type, status="running", payload=payload,
        ))

    def complete(self, db: Session, job_id: int):
        """Marks a job as successfully completed."""
        db_obj = crud_background_job.get(db, job_id)
        if db_obj:
            crud_background_job.update(db, db_obj, BackgroundJobUpdate(status="completed"))

    def fail(self, db: Session, job_id: int, error: str):
        """
        Marks a job as failed, recording the error in its payload so
        it's visible later without needing to dig through server logs
        for what happened at that specific timestamp.
        """
        db_obj = crud_background_job.get(db, job_id)
        if db_obj:
            crud_background_job.update(db, db_obj, BackgroundJobUpdate(status="failed", payload=f"ERROR: {error}"))

background_job_service = BackgroundJobService()
