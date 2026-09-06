# ER-ServiceDesk/app/crud/ticket_part.py
"""
Database access layer for part requirements attached to tickets.
"""

from sqlalchemy.orm import Session
from app.models.ticket_part import TicketPart
from app.schemas.ticket_part import TicketPartCreate, TicketPartUpdate

class TicketPartCRUD:
    """Direct database access for TicketPart records."""

    def get(self, db: Session, id: int) -> TicketPart | None:
        return db.query(TicketPart).filter(TicketPart.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(TicketPart).offset(skip).limit(limit).all()

    def get_by_ticket(self, db: Session, ticket_id: int):
        return db.query(TicketPart).filter(TicketPart.ticket_id == ticket_id).all()

    def create(self, db: Session, obj_in: TicketPartCreate) -> TicketPart:
        obj = TicketPart(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketPart, obj_in: TicketPartUpdate) -> TicketPart:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(TicketPart).filter(TicketPart.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_part = TicketPartCRUD()
