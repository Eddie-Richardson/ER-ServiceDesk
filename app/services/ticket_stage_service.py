# ER-ServiceDesk/app/services/ticket_stage_service.py
# Service layer for TicketStage.
"""
Business logic for TicketStage operations.
"""

from sqlalchemy.orm import Session
from app.crud.ticket_stage import crud_ticket_stage
from app.schemas.ticket_stage import TicketStageCreate, TicketStageUpdate

class TicketStageService:
    """Business logic for TicketStage operations."""

    def get(self, db: Session, id: int):
        return crud_ticket_stage.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_ticket_stage.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketStageCreate):
        return crud_ticket_stage.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketStageUpdate):
        db_obj = crud_ticket_stage.get(db, id)
        return crud_ticket_stage.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_ticket_stage.delete(db, id)

ticket_stage_service = TicketStageService()
