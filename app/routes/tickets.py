# ER-ServiceDesk/app/routes/tickets.py
# API routes for Ticket operations.
"""
REST endpoints for a support/repair job tracked from intake to completion.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ticket_service import ticket_service
from app.schemas.ticket import Ticket, TicketCreate, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/", response_model=list[Ticket])
def list_tickets(db: Session = Depends(get_db)):
    """
    List a support/repair job tracked from intake to completion, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Ticket records.
    """
    return ticket_service.get_multi(db)

@router.get("/{id}", response_model=Ticket)
def get_ticket(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Ticket record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Ticket record.
    """
    return ticket_service.get(db, id)

@router.post("/", response_model=Ticket)
def create_ticket(obj_in: TicketCreate, db: Session = Depends(get_db)):
    """
    Create a new Ticket record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Ticket record.
    """
    return ticket_service.create(db, obj_in)

@router.put("/{id}", response_model=Ticket)
def update_ticket(id: int, obj_in: TicketUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Ticket record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Ticket record.
    """
    return ticket_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket(id: int, db: Session = Depends(get_db)):
    """
    Delete a Ticket record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return ticket_service.delete(db, id)
