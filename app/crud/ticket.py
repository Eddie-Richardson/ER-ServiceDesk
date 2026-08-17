# ER-ServiceDesk/app/crud/ticket.py
# CRUD operations for the Ticket model.
"""
Database access layer for a support/repair job tracked from intake to completion.

Deliberately no delete() -- every table referencing a ticket, including
StatusHistory, has ON DELETE NO ACTION at the database level, so
deleting a ticket with any history/notes/etc. attached would simply
fail at the database. Tickets are meant to only ever be closed via
status, never hard-deleted, so the capability is removed entirely
rather than picking a cascade policy for customer conversation history.
"""

from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketCRUD:
    """Direct database access for Ticket records."""

    def get(self, db: Session, id: int) -> Ticket | None:
        return db.query(Ticket).filter(Ticket.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Ticket).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketCreate) -> Ticket:
        obj = Ticket(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Ticket, obj_in: TicketUpdate) -> Ticket:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

crud_ticket = TicketCRUD()
