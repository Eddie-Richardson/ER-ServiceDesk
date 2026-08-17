# ER-ServiceDesk/app/crud/background_job.py
# CRUD operations for the BackgroundJob model -- get, create, and update only.
"""
Database access layer for an asynchronous job tracked for the RQ worker system.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.

Deliberately no delete() -- job history shouldn't be erasable, matching
the same reasoning as StatusHistory and AuditLog. update() IS kept
(unlike those two), since a job's own status genuinely needs to
transition (queued -> running -> completed/failed) as it actually
runs -- but it's only ever called internally by
background_job_service's own start/complete/fail helpers, never
exposed through a public route (see routes/background_jobs.py).
"""

from sqlalchemy.orm import Session
from app.models.background_job import BackgroundJob
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobCRUD:
    """Direct database access for BackgroundJob records -- read, create, and update only."""

    def get(self, db: Session, id: int) -> BackgroundJob | None:
        return db.query(BackgroundJob).filter(BackgroundJob.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200, job_type: str | None = None, status: str | None = None):
        """
        Fetch multiple BackgroundJob records with simple offset
        pagination, newest first, optionally filtered.

        Args:
            job_type: If given, only jobs of this type.
            status: If given, only jobs currently in this status.
        """
        query = db.query(BackgroundJob)
        if job_type is not None:
            query = query.filter(BackgroundJob.job_type == job_type)
        if status is not None:
            query = query.filter(BackgroundJob.status == status)
        return query.order_by(BackgroundJob.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: BackgroundJobCreate) -> BackgroundJob:
        obj = BackgroundJob(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: BackgroundJob, obj_in: BackgroundJobUpdate) -> BackgroundJob:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

crud_background_job = BackgroundJobCRUD()
