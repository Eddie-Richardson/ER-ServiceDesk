# ER-ServiceDesk/app/crud/ticket_type.py
# CRUD operations for the TicketType model.
#
# Provides database access for creating, reading, updating, and deleting TicketType records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.ticket_type import TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeCRUD:
    # Retrieves a single TicketType by ID.
    def get(self, db: Session, id: int) -> TicketType | None:
        """
        Returns a single TicketType instance matching the given ID.
        """
        return db.query(TicketType).filter(TicketType.id == id).first()

    # Retrieves multiple TicketType records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketType records with pagination support.
        """
        return db.query(TicketType).offset(skip).limit(limit).all()

    # Creates a new TicketType record.
    def create(self, db: Session, obj_in: TicketTypeCreate) -> TicketType:
        """
        Creates a new TicketType using the provided input schema.
        """
        obj = TicketType(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing TicketType record.
    def update(self, db: Session, db_obj: TicketType, obj_in: TicketTypeUpdate) -> TicketType:
        """
        Updates the given TicketType instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a TicketType record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the TicketType instance matching the given ID.
        """
        obj = db.query(TicketType).filter(TicketType.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_type = TicketTypeCRUD()
