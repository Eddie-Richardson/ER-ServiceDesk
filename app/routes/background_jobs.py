# ER-ServiceDesk/app/routes/background_jobs.py
# API routes for BackgroundJob operations.
#
# Exposes REST endpoints for interacting with BackgroundJob records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.background_job_service import background_job_service
from app.schemas.background_job import BackgroundJob, BackgroundJobCreate, BackgroundJobUpdate

router = APIRouter(prefix="/background_jobs", tags=["background_jobs"])

@router.get("/", response_model=list[BackgroundJob])
def list_background_jobs(db: Session = Depends(get_db)):
    """
    Returns a list of BackgroundJob records.
    """
    return background_job_service.get_multi(db)

@router.get("/{id}", response_model=BackgroundJob)
def get_background_job(id: int, db: Session = Depends(get_db)):
    """
    Returns a single BackgroundJob record by ID.
    """
    return background_job_service.get(db, id)

@router.post("/", response_model=BackgroundJob)
def create_background_job(obj_in: BackgroundJobCreate, db: Session = Depends(get_db)):
    """
    Creates a new BackgroundJob record.
    """
    return background_job_service.create(db, obj_in)

@router.put("/{id}", response_model=BackgroundJob)
def update_background_job(id: int, obj_in: BackgroundJobUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing BackgroundJob record.
    """
    return background_job_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_background_job(id: int, db: Session = Depends(get_db)):
    """
    Deletes a BackgroundJob record by ID.
    """
    return background_job_service.delete(db, id)
