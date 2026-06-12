# ER-ServiceDesk/app/routes/tickets.py
# API routes for Ticket operations.
#
# Exposes REST endpoints for interacting with Ticket records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ticket_service import ticket_service
from app.schemas.ticket import Ticket, TicketCreate, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/", response_model=list[Ticket])
def list_tickets(db: Session = Depends(get_db)):
    """
    Returns a list of Ticket records.
    """
    return ticket_service.get_multi(db)

@router.get("/{id}", response_model=Ticket)
def get_ticket(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Ticket record by ID.
    """
    return ticket_service.get(db, id)

@router.post("/", response_model=Ticket)
def create_ticket(obj_in: TicketCreate, db: Session = Depends(get_db)):
    """
    Creates a new Ticket record.
    """
    return ticket_service.create(db, obj_in)

@router.put("/{id}", response_model=Ticket)
def update_ticket(id: int, obj_in: TicketUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Ticket record.
    """
    return ticket_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Ticket record by ID.
    """
    return ticket_service.delete(db, id)
