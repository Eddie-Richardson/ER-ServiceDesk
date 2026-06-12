# ER-ServiceDesk/app/crud/ticket_category.py
# CRUD operations for the TicketCategory model.
#
# Provides database access for creating, reading, updating, and deleting TicketCategory records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.ticket_category import TicketCategory
from app.schemas.ticket_category import TicketCategoryCreate, TicketCategoryUpdate

class TicketCategoryCRUD:
    # Retrieves a single TicketCategory by ID.
    def get(self, db: Session, id: int) -> TicketCategory | None:
        """
        Returns a single TicketCategory instance matching the given ID.
        """
        return db.query(TicketCategory).filter(TicketCategory.id == id).first()

    # Retrieves multiple TicketCategory records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketCategory records with pagination support.
        """
        return db.query(TicketCategory).offset(skip).limit(limit).all()

    # Creates a new TicketCategory record.
    def create(self, db: Session, obj_in: TicketCategoryCreate) -> TicketCategory:
        """
        Creates a new TicketCategory using the provided input schema.
        """
        obj = TicketCategory(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing TicketCategory record.
    def update(self, db: Session, db_obj: TicketCategory, obj_in: TicketCategoryUpdate) -> TicketCategory:
        """
        Updates the given TicketCategory instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a TicketCategory record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the TicketCategory instance matching the given ID.
        """
        obj = db.query(TicketCategory).filter(TicketCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_category = TicketCategoryCRUD()
