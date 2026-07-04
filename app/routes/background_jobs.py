# ER-ServiceDesk/app/routes/background_jobs.py
# API routes for BackgroundJob operations.
"""
REST endpoints for an asynchronous job tracked for the RQ worker system.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.background_job_service import background_job_service
from app.schemas.background_job import BackgroundJob, BackgroundJobCreate, BackgroundJobUpdate

router = APIRouter(prefix="/background_jobs", tags=["background_jobs"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[BackgroundJob])
def list_background_jobs(db: Session = Depends(get_db)):
    """
    List an asynchronous job tracked for the RQ worker system, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of BackgroundJob records.
    """
    return background_job_service.get_multi(db)

@router.get("/{id}", response_model=BackgroundJob)
def get_background_job(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single BackgroundJob record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching BackgroundJob record.
    """
    return background_job_service.get(db, id)

@router.post("/", response_model=BackgroundJob)
def create_background_job(obj_in: BackgroundJobCreate, db: Session = Depends(get_db)):
    """
    Create a new BackgroundJob record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created BackgroundJob record.
    """
    return background_job_service.create(db, obj_in)

@router.put("/{id}", response_model=BackgroundJob)
def update_background_job(id: int, obj_in: BackgroundJobUpdate, db: Session = Depends(get_db)):
    """
    Update an existing BackgroundJob record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated BackgroundJob record.
    """
    return background_job_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_background_job(id: int, db: Session = Depends(get_db)):
    """
    Delete a BackgroundJob record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return background_job_service.delete(db, id)
