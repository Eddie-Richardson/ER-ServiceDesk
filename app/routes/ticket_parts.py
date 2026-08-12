# ER-ServiceDesk/app/routes/ticket_parts.py
# API routes for TicketPart operations.
"""
REST endpoints for TicketPart records.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.ticket_part_service import ticket_part_service
from app.schemas.ticket_part import TicketPart, TicketPartCreate, TicketPartUpdate

router = APIRouter(prefix="/ticket_parts", tags=["ticket_parts"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[TicketPart])
def list_ticket_parts(ticket_id: int | None = None, db: Session = Depends(get_db)):
    """
    List TicketPart records, paginated, optionally filtered to a
    single ticket.

    Args:
        ticket_id: If given, only part requirements for this ticket.
        db: Injected database session.
    """
    if ticket_id is not None:
        return ticket_part_service.get_by_ticket(db, ticket_id)
    return ticket_part_service.get_multi(db)

@router.get("/{id}", response_model=TicketPart)
def get_ticket_part(id: int, db: Session = Depends(get_db)):
    """Fetch a single TicketPart record by ID."""
    return ticket_part_service.get(db, id)

@router.post("/", response_model=TicketPart)
def create_ticket_part(obj_in: TicketPartCreate, db: Session = Depends(get_db)):
    """Create a new TicketPart record."""
    return ticket_part_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketPart)
def update_ticket_part(id: int, obj_in: TicketPartUpdate, db: Session = Depends(get_db)):
    """Update an existing TicketPart record."""
    return ticket_part_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_part(id: int, db: Session = Depends(get_db)):
    """Delete a TicketPart record by ID."""
    return ticket_part_service.delete(db, id)
