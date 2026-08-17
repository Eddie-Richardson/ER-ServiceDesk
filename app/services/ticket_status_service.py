# ER-ServiceDesk/app/services/ticket_status_service.py
# Service layer for TicketStatus.
"""
Business logic for a workflow state a ticket can occupy.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_status import crud_ticket_status
from app.schemas.ticket_status import TicketStatusCreate, TicketStatusUpdate

class TicketStatusService:
    """Business logic for TicketStatus operations."""

    def get(self, db: Session, id: int):
        return crud_ticket_status.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_ticket_status.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketStatusCreate):
        return crud_ticket_status.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketStatusUpdate):
        db_obj = crud_ticket_status.get(db, id)
        return crud_ticket_status.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_ticket_status.delete(db, id)

ticket_status_service = TicketStatusService()
