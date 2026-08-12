# ER-ServiceDesk/app/crud/ticket.py
# CRUD operations for the Ticket model.
"""
Database access layer for a support/repair job tracked from intake to completion.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.

Deliberately no delete() -- a real ticket deletion attempt uncovered a
genuine bug (every table referencing a ticket, including StatusHistory,
has ON DELETE NO ACTION at the database level, so deleting a ticket
with any history/notes/etc. attached would simply fail). Rather than
picking a cascade policy for customer conversation history, confirmed
this was never reachable from the desktop app at all, and tickets are
meant to only ever be closed via status, never hard-deleted -- so the
capability is removed entirely instead of patched.
"""

from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketCRUD:
    """Direct database access for Ticket records."""

    def get(self, db: Session, id: int) -> Ticket | None:
        """
        Fetch a single Ticket by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Ticket instance, or None if no record exists.
        """
        return db.query(Ticket).filter(Ticket.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Ticket records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Ticket instances.
        """
        return db.query(Ticket).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketCreate) -> Ticket:
        """
        Insert a new Ticket record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Ticket instance.
        """
        obj = Ticket(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Ticket, obj_in: TicketUpdate) -> Ticket:
        """
        Apply a partial update to an existing Ticket record.

        Args:
            db: Active database session.
            db_obj: The existing Ticket instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Ticket instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

crud_ticket = TicketCRUD()
