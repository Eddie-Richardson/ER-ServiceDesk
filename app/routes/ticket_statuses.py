# ER-ServiceDesk/app/routes/ticket_status.py
# API routes for TicketStatus operations.
"""
REST endpoints for a workflow state a ticket can occupy.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ticket_status_service import ticket_status_service
from app.schemas.ticket_status import TicketStatus, TicketStatusCreate, TicketStatusUpdate

router = APIRouter(prefix="/ticket_statuses", tags=["ticket_statuses"])

@router.get("/", response_model=list[TicketStatus])
def list_ticket_statuss(db: Session = Depends(get_db)):
    """
    List a workflow state a ticket can occupy, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of TicketStatus records.
    """
    return ticket_status_service.get_multi(db)

@router.get("/{id}", response_model=TicketStatus)
def get_ticket_status(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single TicketStatus record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching TicketStatus record.
    """
    return ticket_status_service.get(db, id)

@router.post("/", response_model=TicketStatus)
def create_ticket_status(obj_in: TicketStatusCreate, db: Session = Depends(get_db)):
    """
    Create a new TicketStatus record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created TicketStatus record.
    """
    return ticket_status_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketStatus)
def update_ticket_status(id: int, obj_in: TicketStatusUpdate, db: Session = Depends(get_db)):
    """
    Update an existing TicketStatus record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated TicketStatus record.
    """
    return ticket_status_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_status(id: int, db: Session = Depends(get_db)):
    """
    Delete a TicketStatus record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return ticket_status_service.delete(db, id)
