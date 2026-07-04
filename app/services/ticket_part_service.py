# ER-ServiceDesk/app/services/ticket_part_service.py
# Service layer for TicketPart.
"""
Business logic for TicketPart operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_part import crud_ticket_part
from app.schemas.ticket_part import TicketPartCreate, TicketPartUpdate

class TicketPartService:
    """Business logic for TicketPart operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single TicketPart by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketPart instance, or None if not found.
        """
        return crud_ticket_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of TicketPart records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketPart instances.
        """
        return crud_ticket_part.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketPartCreate):
        """
        Create a new TicketPart using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created TicketPart instance.
        """
        return crud_ticket_part.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketPartUpdate):
        """
        Update an existing TicketPart using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated TicketPart instance.
        """
        db_obj = crud_ticket_part.get(db, id)
        return crud_ticket_part.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a TicketPart by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket_part.delete(db, id)

ticket_part_service = TicketPartService()
