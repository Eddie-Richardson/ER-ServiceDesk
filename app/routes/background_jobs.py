# ER-ServiceDesk/app/routes/background_jobs.py
# API routes for BackgroundJob -- read-only.
"""
Read-only REST endpoint for background job run history.

Deliberately no create/update/delete route -- entries are only ever
written internally, via background_job_service's own start/complete/
fail helpers, called directly from app/workers/tasks.py as each task
actually runs. Allowing external creation or editing of job records
would make this history untrustworthy (e.g. a failed job could be
silently marked "completed" through the API, hiding a real problem).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.background_job_service import background_job_service
from app.schemas.background_job import BackgroundJob

router = APIRouter(prefix="/background_jobs", tags=["background_jobs"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[BackgroundJob])
def list_background_jobs(
    job_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Most recent first, optionally filtered.

    Args:
        job_type: If given, only jobs of this type.
        status: If given, only jobs currently in this status.
    """
    return background_job_service.get_multi(db, job_type=job_type, status=status)

@router.get("/{id}", response_model=BackgroundJob)
def get_background_job(id: int, db: Session = Depends(get_db)):
    return background_job_service.get(db, id)
