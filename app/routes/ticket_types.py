# ER-ServiceDesk/app/routes/ticket_types.py
"""
REST endpoints for a classification of the kind of work a ticket represents.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.ticket_type_service import ticket_type_service
from app.schemas.ticket_type import TicketType, TicketTypeCreate, TicketTypeUpdate

router = APIRouter(prefix="/ticket_types", tags=["ticket_types"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[TicketType])
def list_ticket_types(db: Session = Depends(get_db)):
    return ticket_type_service.get_multi(db)

@router.get("/{id}", response_model=TicketType)
def get_ticket_type(id: int, db: Session = Depends(get_db)):
    return ticket_type_service.get(db, id)

@router.post("/", response_model=TicketType)
def create_ticket_type(obj_in: TicketTypeCreate, db: Session = Depends(get_db)):
    return ticket_type_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketType)
def update_ticket_type(id: int, obj_in: TicketTypeUpdate, db: Session = Depends(get_db)):
    return ticket_type_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_type(id: int, db: Session = Depends(get_db)):
    return ticket_type_service.delete(db, id)
