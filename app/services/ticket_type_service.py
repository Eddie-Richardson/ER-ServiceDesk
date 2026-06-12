# ER-ServiceDesk/app/services/ticket_type_service.py
# Service layer for TicketType.
#
# Provides business logic for TicketType operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.ticket_type import crud_ticket_type
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeService:
    # Retrieves a single TicketType by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single TicketType instance.
        """
        return crud_ticket_type.get(db, id)

    # Retrieves multiple TicketType records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketType records.
        """
        return crud_ticket_type.get_multi(db, skip, limit)

    # Creates a new TicketType.
    def create(self, db: Session, obj_in: TicketTypeCreate):
        """
        Creates a new TicketType using validated input data.
        """
        return crud_ticket_type.create(db, obj_in)

    # Updates an existing TicketType.
    def update(self, db: Session, id: int, obj_in: TicketTypeUpdate):
        """
        Updates an existing TicketType using validated input data.
        """
        db_obj = crud_ticket_type.get(db, id)
        return crud_ticket_type.update(db, db_obj, obj_in)

    # Deletes a TicketType by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a TicketType instance.
        """
        return crud_ticket_type.delete(db, id)

ticket_type_service = TicketTypeService()
