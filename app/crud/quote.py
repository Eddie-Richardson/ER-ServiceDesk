# ER-ServiceDesk/app/crud/quote.py
# CRUD operations for the Quote model.
#
# Provides database access for creating, reading, updating, and deleting Quote records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.quote import Quote
from app.schemas.quote import QuoteCreate, QuoteUpdate

class QuoteCRUD:
    # Retrieves a single Quote by ID.
    def get(self, db: Session, id: int) -> Quote | None:
        """
        Returns a single Quote instance matching the given ID.
        """
        return db.query(Quote).filter(Quote.id == id).first()

    # Retrieves multiple Quote records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Quote records with pagination support.
        """
        return db.query(Quote).offset(skip).limit(limit).all()

    # Creates a new Quote record.
    def create(self, db: Session, obj_in: QuoteCreate) -> Quote:
        """
        Creates a new Quote using the provided input schema.
        """
        obj = Quote(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Quote record.
    def update(self, db: Session, db_obj: Quote, obj_in: QuoteUpdate) -> Quote:
        """
        Updates the given Quote instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Quote record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Quote instance matching the given ID.
        """
        obj = db.query(Quote).filter(Quote.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_quote = QuoteCRUD()
