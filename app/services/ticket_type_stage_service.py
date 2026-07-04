# ER-ServiceDesk/app/services/ticket_type_stage_service.py
# Service layer for TicketTypeStage.
"""
Business logic for the ticket-type-to-stage allow-list.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_type_stage import crud_ticket_type_stage
from app.schemas.ticket_type_stage import TicketTypeStageCreate, TicketTypeStageUpdate

class TicketTypeStageService:
    """Business logic for TicketTypeStage operations."""

    def get(self, db: Session, id: int):
        """Fetch a single TicketTypeStage by ID."""
        return crud_ticket_type_stage.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """Fetch a page of TicketTypeStage records."""
        return crud_ticket_type_stage.get_multi(db, skip, limit)

    def get_for_type(self, db: Session, type_id: int):
        """Fetch every stage allowed for a given ticket type."""
        return crud_ticket_type_stage.get_for_type(db, type_id)

    def create(self, db: Session, obj_in: TicketTypeStageCreate):
        """Create a new allow-list entry using validated input data."""
        return crud_ticket_type_stage.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketTypeStageUpdate):
        """Update an existing allow-list entry using validated input data."""
        db_obj = crud_ticket_type_stage.get(db, id)
        return crud_ticket_type_stage.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """Delete an allow-list entry by ID."""
        return crud_ticket_type_stage.delete(db, id)

ticket_type_stage_service = TicketTypeStageService()
