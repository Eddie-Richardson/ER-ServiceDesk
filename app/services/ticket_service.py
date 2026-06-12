# ER-ServiceDesk/app/services/ticket_service.py
# Service layer for Ticket.
#
# Provides business logic for Ticket operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.ticket import crud_ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketService:
    # Retrieves a single Ticket by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Ticket instance.
        """
        return crud_ticket.get(db, id)

    # Retrieves multiple Ticket records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Ticket records.
        """
        return crud_ticket.get_multi(db, skip, limit)

    # Creates a new Ticket.
    def create(self, db: Session, obj_in: TicketCreate):
        """
        Creates a new Ticket using validated input data.
        """
        return crud_ticket.create(db, obj_in)

    # Updates an existing Ticket.
    def update(self, db: Session, id: int, obj_in: TicketUpdate):
        """
        Updates an existing Ticket using validated input data.
        """
        db_obj = crud_ticket.get(db, id)
        return crud_ticket.update(db, db_obj, obj_in)

    # Deletes a Ticket by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Ticket instance.
        """
        return crud_ticket.delete(db, id)

ticket_service = TicketService()
