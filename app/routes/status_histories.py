# ER-ServiceDesk/app/routes/status_histories.py
# API routes for StatusHistory operations.
#
# Exposes REST endpoints for interacting with StatusHistory records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.status_history_service import status_history_service
from app.schemas.status_history import StatusHistory, StatusHistoryCreate, StatusHistoryUpdate

router = APIRouter(prefix="/status_histories", tags=["status_histories"])

@router.get("/", response_model=list[StatusHistory])
def list_status_histories(db: Session = Depends(get_db)):
    """
    Returns a list of StatusHistory records.
    """
    return status_history_service.get_multi(db)

@router.get("/{id}", response_model=StatusHistory)
def get_status_history(id: int, db: Session = Depends(get_db)):
    """
    Returns a single StatusHistory record by ID.
    """
    return status_history_service.get(db, id)

@router.post("/", response_model=StatusHistory)
def create_status_history(obj_in: StatusHistoryCreate, db: Session = Depends(get_db)):
    """
    Creates a new StatusHistory record.
    """
    return status_history_service.create(db, obj_in)

@router.put("/{id}", response_model=StatusHistory)
def update_status_history(id: int, obj_in: StatusHistoryUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing StatusHistory record.
    """
    return status_history_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_status_history(id: int, db: Session = Depends(get_db)):
    """
    Deletes a StatusHistory record by ID.
    """
    return status_history_service.delete(db, id)
