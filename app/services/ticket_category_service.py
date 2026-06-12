# ER-ServiceDesk/app/services/ticket_category_service.py
# Service layer for TicketCategory.
#
# Provides business logic for TicketCategory operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.ticket_category import crud_ticket_category
from app.schemas.ticket_category import TicketCategoryCreate, TicketCategoryUpdate

class TicketCategoryService:
    # Retrieves a single TicketCategory by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single TicketCategory instance.
        """
        return crud_ticket_category.get(db, id)

    # Retrieves multiple TicketCategory records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketCategory records.
        """
        return crud_ticket_category.get_multi(db, skip, limit)

    # Creates a new TicketCategory.
    def create(self, db: Session, obj_in: TicketCategoryCreate):
        """
        Creates a new TicketCategory using validated input data.
        """
        return crud_ticket_category.create(db, obj_in)

    # Updates an existing TicketCategory.
    def update(self, db: Session, id: int, obj_in: TicketCategoryUpdate):
        """
        Updates an existing TicketCategory using validated input data.
        """
        db_obj = crud_ticket_category.get(db, id)
        return crud_ticket_category.update(db, db_obj, obj_in)

    # Deletes a TicketCategory by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a TicketCategory instance.
        """
        return crud_ticket_category.delete(db, id)

ticket_category_service = TicketCategoryService()
