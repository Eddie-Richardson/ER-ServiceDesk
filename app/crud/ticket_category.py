# ER-ServiceDesk/app/crud/ticket_category.py
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
        return db.query(TicketCategory).filter(TicketCategory.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(TicketCategory).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketCategoryCreate) -> TicketCategory:
        obj = TicketCategory(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketCategory, obj_in: TicketCategoryUpdate) -> TicketCategory:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(TicketCategory).filter(TicketCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_category = TicketCategoryCRUD()
