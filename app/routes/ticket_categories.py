# ER-ServiceDesk/app/routes/ticket_categorys.py
# API routes for TicketCategory operations.
"""
REST endpoints for a high-level grouping used to organize tickets.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.ticket_category_service import ticket_category_service
from app.schemas.ticket_category import TicketCategory, TicketCategoryCreate, TicketCategoryUpdate

router = APIRouter(prefix="/ticket_categories", tags=["ticket_categories"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[TicketCategory])
def list_ticket_categorys(db: Session = Depends(get_db)):
    """
    List a high-level grouping used to organize tickets, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of TicketCategory records.
    """
    return ticket_category_service.get_multi(db)

@router.get("/{id}", response_model=TicketCategory)
def get_ticket_category(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single TicketCategory record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching TicketCategory record.
    """
    return ticket_category_service.get(db, id)

@router.post("/", response_model=TicketCategory)
def create_ticket_category(obj_in: TicketCategoryCreate, db: Session = Depends(get_db)):
    """
    Create a new TicketCategory record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created TicketCategory record.
    """
    return ticket_category_service.create(db, obj_in)

@router.put("/{id}", response_model=TicketCategory)
def update_ticket_category(id: int, obj_in: TicketCategoryUpdate, db: Session = Depends(get_db)):
    """
    Update an existing TicketCategory record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated TicketCategory record.
    """
    return ticket_category_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_ticket_category(id: int, db: Session = Depends(get_db)):
    """
    Delete a TicketCategory record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return ticket_category_service.delete(db, id)
