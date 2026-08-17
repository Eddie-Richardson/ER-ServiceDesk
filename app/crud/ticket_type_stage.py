# ER-ServiceDesk/app/crud/ticket_type_stage.py
# CRUD operations for the TicketTypeStage model.
"""
Database access layer for the ticket-type-to-stage allow-list.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ticket_type_stage import TicketTypeStage
from app.schemas.ticket_type_stage import TicketTypeStageCreate, TicketTypeStageUpdate

class TicketTypeStageCRUD:
    """Direct database access for TicketTypeStage records."""

    def get(self, db: Session, id: int) -> TicketTypeStage | None:
        return db.query(TicketTypeStage).filter(TicketTypeStage.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(TicketTypeStage).offset(skip).limit(limit).all()

    def get_for_type(self, db: Session, type_id: int):
        return db.query(TicketTypeStage).filter(TicketTypeStage.type_id == type_id).all()

    def is_allowed(self, db: Session, type_id: int, stage_id: int) -> bool:
        return db.query(TicketTypeStage).filter(
            TicketTypeStage.type_id == type_id,
            TicketTypeStage.stage_id == stage_id,
        ).first() is not None

    def create(self, db: Session, obj_in: TicketTypeStageCreate) -> TicketTypeStage:
        """
        Raises:
            HTTPException: 400 if this (type_id, stage_id) pair already exists.
        """
        existing = db.query(TicketTypeStage).filter(
            TicketTypeStage.type_id == obj_in.type_id,
            TicketTypeStage.stage_id == obj_in.stage_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This stage is already allowed for this ticket type",
            )
        obj = TicketTypeStage(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketTypeStage, obj_in: TicketTypeStageUpdate) -> TicketTypeStage:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(TicketTypeStage).filter(TicketTypeStage.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_type_stage = TicketTypeStageCRUD()
