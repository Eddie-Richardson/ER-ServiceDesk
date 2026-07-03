# ER-ServiceDesk/app/services/quote_service.py
# Service layer for Quote.
"""
Business logic for an estimated price for ticket-related work, pending customer approval.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.quote import crud_quote
from app.schemas.quote import QuoteCreate, QuoteUpdate

class QuoteService:
    """Business logic for Quote operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Quote by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Quote instance, or None if not found.
        """
        return crud_quote.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Quote records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Quote instances.
        """
        return crud_quote.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: QuoteCreate):
        """
        Create a new Quote using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Quote instance.
        """
        return crud_quote.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: QuoteUpdate):
        """
        Update an existing Quote using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Quote instance.
        """
        db_obj = crud_quote.get(db, id)
        return crud_quote.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Quote by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_quote.delete(db, id)

quote_service = QuoteService()
