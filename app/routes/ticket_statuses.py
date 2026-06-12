# ER-ServiceDesk/app/routes/ticket_statuses.py
# API routes for TicketStatus operations.
#
# Exposes REST endpoints for interacting with TicketStatus records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ticket_status_service import ticket_status_service
from app.schemas.ticket_status import TicketStatus, TicketStatusCreate, TicketStatusUpdate

router = APIRouter(prefix="/ticket_statuses", tags=["ticket_statuses"])

@router.get("/", response_model=list[TicketStatus])
def list_ticket_statuses(db: Session = Depends(get_db)):
    """
    Returns a list of TicketStatus records.
    """
    return ticket_status_service.get_multi(db)

@router.get("/{id}", response_model=TicketStatus)
def get_ticket_status(id: int, db: Session = Depends(get_db)):
    """
    Returns a single TicketStatus record by ID.
    """
    return ticket_status_service.get(db, id)

@router.post("/", response_model=TicketStatus)
def create_ticket_status(obj_in: TicketStatusCreate, db: Session = Depends(get_db)):
    """
    Creates a new TicketStatus record.
    """
    return ticket_status_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketStatus)
def update_ticket_status(id: int, obj_in: TicketStatusUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing TicketStatus record.
    """
    return ticket_status_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_status(id: int, db: Session = Depends(get_db)):
    """
    Deletes a TicketStatus record by ID.
    """
    return ticket_status_service.delete(db, id)
