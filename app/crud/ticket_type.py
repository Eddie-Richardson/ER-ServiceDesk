# ER-ServiceDesk/app/crud/ticket_type.py
# CRUD operations for the TicketType model.
"""
Database access layer for a classification of the kind of work a ticket represents.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.ticket_type import TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeCRUD:
    """Direct database access for TicketType records."""

    def get(self, db: Session, id: int) -> TicketType | None:
        """
        Fetch a single TicketType by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketType instance, or None if no record exists.
        """
        return db.query(TicketType).filter(TicketType.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple TicketType records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketType instances.
        """
        return db.query(TicketType).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketTypeCreate) -> TicketType:
        """
        Insert a new TicketType record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed TicketType instance.
        """
        obj = TicketType(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketType, obj_in: TicketTypeUpdate) -> TicketType:
        """
        Apply a partial update to an existing TicketType record.

        Args:
            db: Active database session.
            db_obj: The existing TicketType instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed TicketType instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a TicketType record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(TicketType).filter(TicketType.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_type = TicketTypeCRUD()
