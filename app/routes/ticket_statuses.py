# ER-ServiceDesk/app/routes/ticket_statuses.py
"""
REST endpoints for a workflow state a ticket can occupy.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.ticket_status_service import ticket_status_service
from app.schemas.ticket_status import TicketStatus, TicketStatusCreate, TicketStatusUpdate

router = APIRouter(prefix="/ticket_statuses", tags=["ticket_statuses"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[TicketStatus])
def list_ticket_statuses(db: Session = Depends(get_db)):
    return ticket_status_service.get_multi(db)

@router.get("/{id}", response_model=TicketStatus)
def get_ticket_status(id: int, db: Session = Depends(get_db)):
    return ticket_status_service.get(db, id)

@router.post("/", response_model=TicketStatus)
def create_ticket_status(obj_in: TicketStatusCreate, db: Session = Depends(get_db)):
    return ticket_status_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketStatus)
def update_ticket_status(id: int, obj_in: TicketStatusUpdate, db: Session = Depends(get_db)):
    return ticket_status_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_status(id: int, db: Session = Depends(get_db)):
    return ticket_status_service.delete(db, id)
