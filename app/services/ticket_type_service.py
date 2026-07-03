# ER-ServiceDesk/app/services/ticket_type_service.py
# Service layer for TicketType.
"""
Business logic for a classification of the kind of work a ticket represents.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_type import crud_ticket_type
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeService:
    """Business logic for TicketType operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single TicketType by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketType instance, or None if not found.
        """
        return crud_ticket_type.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of TicketType records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketType instances.
        """
        return crud_ticket_type.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketTypeCreate):
        """
        Create a new TicketType using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created TicketType instance.
        """
        return crud_ticket_type.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketTypeUpdate):
        """
        Update an existing TicketType using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated TicketType instance.
        """
        db_obj = crud_ticket_type.get(db, id)
        return crud_ticket_type.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a TicketType by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket_type.delete(db, id)

ticket_type_service = TicketTypeService()
