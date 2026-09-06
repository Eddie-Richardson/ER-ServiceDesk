# ER-ServiceDesk/app/routes/ticket_categories.py
"""
REST endpoints for a high-level grouping used to organize tickets.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.ticket_category_service import ticket_category_service
from app.schemas.ticket_category import TicketCategory, TicketCategoryCreate, TicketCategoryUpdate

router = APIRouter(prefix="/ticket_categories", tags=["ticket_categories"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[TicketCategory])
def list_ticket_categories(db: Session = Depends(get_db)):
    return ticket_category_service.get_multi(db)

@router.get("/{id}", response_model=TicketCategory)
def get_ticket_category(id: int, db: Session = Depends(get_db)):
    return ticket_category_service.get(db, id)

@router.post("/", response_model=TicketCategory)
def create_ticket_category(obj_in: TicketCategoryCreate, db: Session = Depends(get_db)):
    return ticket_category_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketCategory)
def update_ticket_category(id: int, obj_in: TicketCategoryUpdate, db: Session = Depends(get_db)):
    return ticket_category_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_category(id: int, db: Session = Depends(get_db)):
    return ticket_category_service.delete(db, id)
