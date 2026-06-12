# ER-ServiceDesk/app/services/quote_service.py
# Service layer for Quote.
#
# Provides business logic for Quote operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.quote import crud_quote
from app.schemas.quote import QuoteCreate, QuoteUpdate

class QuoteService:
    # Retrieves a single Quote by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Quote instance.
        """
        return crud_quote.get(db, id)

    # Retrieves multiple Quote records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Quote records.
        """
        return crud_quote.get_multi(db, skip, limit)

    # Creates a new Quote.
    def create(self, db: Session, obj_in: QuoteCreate):
        """
        Creates a new Quote using validated input data.
        """
        return crud_quote.create(db, obj_in)

    # Updates an existing Quote.
    def update(self, db: Session, id: int, obj_in: QuoteUpdate):
        """
        Updates an existing Quote using validated input data.
        """
        db_obj = crud_quote.get(db, id)
        return crud_quote.update(db, db_obj, obj_in)

    # Deletes a Quote by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Quote instance.
        """
        return crud_quote.delete(db, id)

quote_service = QuoteService()
