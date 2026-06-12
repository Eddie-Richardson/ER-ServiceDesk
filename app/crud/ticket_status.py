# ER-ServiceDesk/app/crud/ticket_status.py
# CRUD operations for the TicketStatus model.
#
# Provides database access for creating, reading, updating, and deleting TicketStatus records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.ticket_status import TicketStatus
from app.schemas.ticket_status import TicketStatusCreate, TicketStatusUpdate

class TicketStatusCRUD:
    # Retrieves a single TicketStatus by ID.
    def get(self, db: Session, id: int) -> TicketStatus | None:
        """
        Returns a single TicketStatus instance matching the given ID.
        """
        return db.query(TicketStatus).filter(TicketStatus.id == id).first()

    # Retrieves multiple TicketStatus records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of TicketStatus records with pagination support.
        """
        return db.query(TicketStatus).offset(skip).limit(limit).all()

    # Creates a new TicketStatus record.
    def create(self, db: Session, obj_in: TicketStatusCreate) -> TicketStatus:
        """
        Creates a new TicketStatus using the provided input schema.
        """
        obj = TicketStatus(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing TicketStatus record.
    def update(self, db: Session, db_obj: TicketStatus, obj_in: TicketStatusUpdate) -> TicketStatus:
        """
        Updates the given TicketStatus instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a TicketStatus record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the TicketStatus instance matching the given ID.
        """
        obj = db.query(TicketStatus).filter(TicketStatus.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_status = TicketStatusCRUD()
