# ER-ServiceDesk/app/crud/ticket_category.py
# CRUD operations for the TicketCategory model.
"""
Database access layer for a high-level grouping used to organize tickets.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.ticket_category import TicketCategory
from app.schemas.ticket_category import TicketCategoryCreate, TicketCategoryUpdate

class TicketCategoryCRUD:
    """Direct database access for TicketCategory records."""

    def get(self, db: Session, id: int) -> TicketCategory | None:
        """
        Fetch a single TicketCategory by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketCategory instance, or None if no record exists.
        """
        return db.query(TicketCategory).filter(TicketCategory.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple TicketCategory records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketCategory instances.
        """
        return db.query(TicketCategory).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketCategoryCreate) -> TicketCategory:
        """
        Insert a new TicketCategory record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed TicketCategory instance.
        """
        obj = TicketCategory(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketCategory, obj_in: TicketCategoryUpdate) -> TicketCategory:
        """
        Apply a partial update to an existing TicketCategory record.

        Args:
            db: Active database session.
            db_obj: The existing TicketCategory instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed TicketCategory instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a TicketCategory record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(TicketCategory).filter(TicketCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_category = TicketCategoryCRUD()
