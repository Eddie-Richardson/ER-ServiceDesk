# ER-ServiceDesk/app/services/ticket_type_service.py
"""
Business logic for a classification of the kind of work a ticket represents.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_type import crud_ticket_type
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate

class TicketTypeService:
    """Business logic for TicketType operations."""

    def get(self, db: Session, id: int):
        return crud_ticket_type.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_ticket_type.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketTypeCreate):
        return crud_ticket_type.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketTypeUpdate):
        db_obj = crud_ticket_type.get(db, id)
        return crud_ticket_type.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_ticket_type.delete(db, id)

ticket_type_service = TicketTypeService()
