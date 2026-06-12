# ER-ServiceDesk/app/services/ticket_status_service.py
# Service layer for TicketStatus.
#
# Provides business logic for TicketStatus operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.ticket_status import crud_ticket_status
from app.schemas.ticket_status import TicketStatusCreate, TicketStatusUpdate

class TicketStatusService:
    # Retrieves a single TicketStatus by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single TicketStatus instance.
        """
        return crud_ticket_status.get(db, id)

    # Retrieves multiple TicketStatus records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketStatus records.
        """
        return crud_ticket_status.get_multi(db, skip, limit)

    # Creates a new TicketStatus.
    def create(self, db: Session, obj_in: TicketStatusCreate):
        """
        Creates a new TicketStatus using validated input data.
        """
        return crud_ticket_status.create(db, obj_in)

    # Updates an existing TicketStatus.
    def update(self, db: Session, id: int, obj_in: TicketStatusUpdate):
        """
        Updates an existing TicketStatus using validated input data.
        """
        db_obj = crud_ticket_status.get(db, id)
        return crud_ticket_status.update(db, db_obj, obj_in)

    # Deletes a TicketStatus by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a TicketStatus instance.
        """
        return crud_ticket_status.delete(db, id)

ticket_status_service = TicketStatusService()
