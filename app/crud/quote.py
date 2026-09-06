# ER-ServiceDesk/app/crud/quote.py
"""
Database access layer for an estimated price for ticket-related work, pending customer approval.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.quote import Quote
from app.schemas.quote import QuoteCreate, QuoteUpdate

class QuoteCRUD:
    """Direct database access for Quote records."""

    def get(self, db: Session, id: int) -> Quote | None:
        return db.query(Quote).filter(Quote.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Quote).offset(skip).limit(limit).all()

    def get_by_ticket(self, db: Session, ticket_id: int):
        return db.query(Quote).filter(Quote.ticket_id == ticket_id).all()

    def create(self, db: Session, obj_in: QuoteCreate) -> Quote:
        obj = Quote(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Quote, obj_in: QuoteUpdate) -> Quote:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Quote):
        db.delete(db_obj)
        db.commit()

crud_quote = QuoteCRUD()
