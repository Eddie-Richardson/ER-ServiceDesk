# ER-ServiceDesk/app/routes/ticket_type_stages.py
"""
REST endpoints for managing which TicketStage values are valid for each
TicketType.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.ticket_type_stage_service import ticket_type_stage_service
from app.schemas.ticket_type_stage import TicketTypeStage, TicketTypeStageCreate, TicketTypeStageUpdate

router = APIRouter(prefix="/ticket_type_stages", tags=["ticket_type_stages"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[TicketTypeStage])
def list_ticket_type_stages(db: Session = Depends(get_db)):
    """List every (type, stage) allow-list entry."""
    return ticket_type_stage_service.get_multi(db)

@router.get("/by-type/{type_id}", response_model=list[TicketTypeStage])
def list_stages_for_type(type_id: int, db: Session = Depends(get_db)):
    """List every stage allowed for a given ticket type."""
    return ticket_type_stage_service.get_for_type(db, type_id)

@router.get("/{id}", response_model=TicketTypeStage)
def get_ticket_type_stage(id: int, db: Session = Depends(get_db)):
    """Fetch a single allow-list entry by ID."""
    return ticket_type_stage_service.get(db, id)

@router.post("/", response_model=TicketTypeStage)
def create_ticket_type_stage(obj_in: TicketTypeStageCreate, db: Session = Depends(get_db)):
    """Add a stage to a ticket type's allow-list."""
    return ticket_type_stage_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketTypeStage)
def update_ticket_type_stage(id: int, obj_in: TicketTypeStageUpdate, db: Session = Depends(get_db)):
    """Update an existing allow-list entry."""
    return ticket_type_stage_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_type_stage(id: int, db: Session = Depends(get_db)):
    """Remove a stage from a ticket type's allow-list."""
    return ticket_type_stage_service.delete(db, id)
