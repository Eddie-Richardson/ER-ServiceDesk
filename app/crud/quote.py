# ER-ServiceDesk/app/crud/quote.py
# CRUD operations for the Quote model.
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
        """
        Fetch a single Quote by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Quote instance, or None if no record exists.
        """
        return db.query(Quote).filter(Quote.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Quote records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Quote instances.
        """
        return db.query(Quote).offset(skip).limit(limit).all()

    def get_by_ticket(self, db: Session, ticket_id: int):
        """
        Fetch every quote for a given ticket.

        Args:
            db: Active database session.
            ticket_id: The ticket to look up quotes for.

        Returns:
            A list of Quote instances for that ticket.
        """
        return db.query(Quote).filter(Quote.ticket_id == ticket_id).all()

    def create(self, db: Session, obj_in: QuoteCreate) -> Quote:
        """
        Insert a new Quote record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Quote instance.
        """
        obj = Quote(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Quote, obj_in: QuoteUpdate) -> Quote:
        """
        Apply a partial update to an existing Quote record.

        Args:
            db: Active database session.
            db_obj: The existing Quote instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Quote instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

crud_quote = QuoteCRUD()
