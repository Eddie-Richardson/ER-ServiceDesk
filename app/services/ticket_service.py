# ER-ServiceDesk/app/services/ticket_service.py
# Service layer for Ticket.
"""
Business logic for a support/repair job tracked from intake to completion.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.ticket import crud_ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketService:
    """Business logic for Ticket operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Ticket by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Ticket instance, or None if not found.
        """
        return crud_ticket.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Ticket records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Ticket instances.
        """
        return crud_ticket.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketCreate):
        """
        Create a new Ticket using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Ticket instance.
        """
        return crud_ticket.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketUpdate):
        """
        Update an existing Ticket using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Ticket instance.
        """
        db_obj = crud_ticket.get(db, id)
        return crud_ticket.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Ticket by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket.delete(db, id)

ticket_service = TicketService()
