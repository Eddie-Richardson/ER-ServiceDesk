# ER-ServiceDesk/app/crud/ticket_type.py
"""
Database access layer for a classification of the kind of work a ticket represents.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.ticket_type import TicketType
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeCRUD:
    """Direct database access for TicketType records."""

    def get(self, db: Session, id: int) -> TicketType | None:
        return db.query(TicketType).filter(TicketType.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(TicketType).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketTypeCreate) -> TicketType:
        obj = TicketType(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketType, obj_in: TicketTypeUpdate) -> TicketType:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(TicketType).filter(TicketType.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_type = TicketTypeCRUD()
