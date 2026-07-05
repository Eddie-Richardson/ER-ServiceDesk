# ER-ServiceDesk/app/crud/ticket_status.py
# CRUD operations for the TicketStatus model.
"""
Database access layer for a workflow state a ticket can occupy.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.ticket_status import TicketStatus
from app.schemas.ticket_status import TicketStatusCreate, TicketStatusUpdate

class TicketStatusCRUD:
    """Direct database access for TicketStatus records."""

    def get(self, db: Session, id: int) -> TicketStatus | None:
        """
        Fetch a single TicketStatus by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketStatus instance, or None if no record exists.
        """
        return db.query(TicketStatus).filter(TicketStatus.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple TicketStatus records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketStatus instances.
        """
        return db.query(TicketStatus).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketStatusCreate) -> TicketStatus:
        """
        Insert a new TicketStatus record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed TicketStatus instance.
        """
        obj = TicketStatus(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketStatus, obj_in: TicketStatusUpdate) -> TicketStatus:
        """
        Apply a partial update to an existing TicketStatus record.

        Args:
            db: Active database session.
            db_obj: The existing TicketStatus instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed TicketStatus instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a TicketStatus record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(TicketStatus).filter(TicketStatus.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_status = TicketStatusCRUD()
