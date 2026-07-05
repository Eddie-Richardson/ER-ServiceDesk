# ER-ServiceDesk/app/crud/ticket_stage.py
# CRUD operations for the TicketStage model.
"""
Database access layer for granular ticket work stages.
"""

from sqlalchemy.orm import Session
from app.models.ticket_stage import TicketStage
from app.schemas.ticket_stage import TicketStageCreate, TicketStageUpdate

class TicketStageCRUD:
    """Direct database access for TicketStage records."""

    def get(self, db: Session, id: int) -> TicketStage | None:
        """Fetch a single TicketStage by primary key."""
        return db.query(TicketStage).filter(TicketStage.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """Fetch multiple TicketStage records with simple offset pagination."""
        return db.query(TicketStage).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TicketStageCreate) -> TicketStage:
        """Insert a new TicketStage record."""
        obj = TicketStage(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TicketStage, obj_in: TicketStageUpdate) -> TicketStage:
        """Apply a partial update to an existing TicketStage record."""
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """Delete a TicketStage record by primary key, if it exists."""
        obj = db.query(TicketStage).filter(TicketStage.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_ticket_stage = TicketStageCRUD()
