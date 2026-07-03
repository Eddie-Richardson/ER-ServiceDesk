# ER-ServiceDesk/app/routes/ticket_types.py
# API routes for TicketType operations.
"""
REST endpoints for a classification of the kind of work a ticket represents.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ticket_type_service import ticket_type_service
from app.schemas.ticket_type import TicketType, TicketTypeCreate, TicketTypeUpdate

router = APIRouter(prefix="/ticket_types", tags=["ticket_types"])

@router.get("/", response_model=list[TicketType])
def list_ticket_types(db: Session = Depends(get_db)):
    """
    List a classification of the kind of work a ticket represents, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of TicketType records.
    """
    return ticket_type_service.get_multi(db)

@router.get("/{id}", response_model=TicketType)
def get_ticket_type(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single TicketType record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching TicketType record.
    """
    return ticket_type_service.get(db, id)

@router.post("/", response_model=TicketType)
def create_ticket_type(obj_in: TicketTypeCreate, db: Session = Depends(get_db)):
    """
    Create a new TicketType record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created TicketType record.
    """
    return ticket_type_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketType)
def update_ticket_type(id: int, obj_in: TicketTypeUpdate, db: Session = Depends(get_db)):
    """
    Update an existing TicketType record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated TicketType record.
    """
    return ticket_type_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_type(id: int, db: Session = Depends(get_db)):
    """
    Delete a TicketType record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return ticket_type_service.delete(db, id)
