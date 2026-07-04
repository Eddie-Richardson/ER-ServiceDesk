# ER-ServiceDesk/app/crud/ticket_part.py
# CRUD operations for the TicketPart model.
"""
Database access layer for part requirements attached to tickets.
"""

from sqlalchemy.orm import Session
from app.models.ticket_part import TicketPart
from app.schemas.ticket_part import TicketPartCreate, TicketPartUpdate

class TicketPartCRUD:
    """Direct database access for TicketPart records."""

    def get(self, db: Session, id: int) -> TicketPart | None:
        """
        Fetch a single TicketPart by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketPart instance, or None if not found.
        """
        return db.query(TicketPart).filter(TicketPart.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple TicketPart records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketPart instances.
        """
        return db.query(TicketPart).offset(skip).limit(limit).all()

    def get_by_ticket(self, db: Session, ticket_id: int):
        """
        Fetch every part requirement attached to a given ticket.

        Args:
            db: Active database session.
            ticket_id: The ticket to look up part requirements for.

        Returns:
            A list of TicketPart instances for that ticket.
        """
        return db.query(TicketPart).filter(TicketPart.ticket_id == ticket_id).all()

    def create(self, db: Session, obj_in: TicketPartCreate) -> TicketPart:
        """
        Insert a new TicketPart record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed TicketPart instance.
        """
        obj = TicketPart(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketPart, obj_in: TicketPartUpdate) -> TicketPart:
        """
        Apply a partial update to an existing TicketPart record.

        Args:
            db: Active database session.
            db_obj: The existing TicketPart instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed TicketPart instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a TicketPart record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(TicketPart).filter(TicketPart.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_part = TicketPartCRUD()
