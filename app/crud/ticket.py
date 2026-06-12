# ER-ServiceDesk/app/crud/ticket.py
# CRUD operations for the Ticket model.
#
# Provides database access for creating, reading, updating, and deleting Ticket records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketCRUD:
    # Retrieves a single Ticket by ID.
    def get(self, db: Session, id: int) -> Ticket | None:
        """
        Returns a single Ticket instance matching the given ID.
        """
        return db.query(Ticket).filter(Ticket.id == id).first()

    # Retrieves multiple Ticket records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Ticket records with pagination support.
        """
        return db.query(Ticket).offset(skip).limit(limit).all()

    # Creates a new Ticket record.
    def create(self, db: Session, obj_in: TicketCreate) -> Ticket:
        """
        Creates a new Ticket using the provided input schema.
        """
        obj = Ticket(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Ticket record.
    def update(self, db: Session, db_obj: Ticket, obj_in: TicketUpdate) -> Ticket:
        """
        Updates the given Ticket instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Ticket record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Ticket instance matching the given ID.
        """
        obj = db.query(Ticket).filter(Ticket.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket = TicketCRUD()
