# ER-ServiceDesk/app/services/ticket_category_service.py
# Service layer for TicketCategory.
"""
Business logic for a high-level grouping used to organize tickets.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_category import crud_ticket_category
from app.schemas.ticket_category import TicketCategoryCreate, TicketCategoryUpdate

class TicketCategoryService:
    """Business logic for TicketCategory operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single TicketCategory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketCategory instance, or None if not found.
        """
        return crud_ticket_category.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of TicketCategory records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketCategory instances.
        """
        return crud_ticket_category.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketCategoryCreate):
        """
        Create a new TicketCategory using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created TicketCategory instance.
        """
        return crud_ticket_category.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketCategoryUpdate):
        """
        Update an existing TicketCategory using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated TicketCategory instance.
        """
        db_obj = crud_ticket_category.get(db, id)
        return crud_ticket_category.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a TicketCategory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket_category.delete(db, id)

ticket_category_service = TicketCategoryService()
