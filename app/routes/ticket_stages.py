# ER-ServiceDesk/app/routes/ticket_stages.py
# API routes for TicketStage operations.
"""
REST endpoints for TicketStage records.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.ticket_stage_service import ticket_stage_service
from app.schemas.ticket_stage import TicketStage, TicketStageCreate, TicketStageUpdate

router = APIRouter(prefix="/ticket_stages", tags=["ticket_stages"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[TicketStage])
def list_ticket_stages(db: Session = Depends(get_db)):
    """List TicketStage records, paginated."""
    return ticket_stage_service.get_multi(db)

@router.get("/{id}", response_model=TicketStage)
def get_ticket_stage(id: int, db: Session = Depends(get_db)):
    """Fetch a single TicketStage record by ID."""
    return ticket_stage_service.get(db, id)

@router.post("/", response_model=TicketStage)
def create_ticket_stage(obj_in: TicketStageCreate, db: Session = Depends(get_db)):
    """Create a new TicketStage record."""
    return ticket_stage_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketStage)
def update_ticket_stage(id: int, obj_in: TicketStageUpdate, db: Session = Depends(get_db)):
    """Update an existing TicketStage record."""
    return ticket_stage_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_stage(id: int, db: Session = Depends(get_db)):
    """Delete a TicketStage record by ID."""
    return ticket_stage_service.delete(db, id)
