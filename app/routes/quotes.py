# ER-ServiceDesk/app/routes/quotes.py
# API routes for Quote operations.
"""
REST endpoints for an estimated price for ticket-related work, pending customer approval.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.quote_service import quote_service
from app.schemas.quote import Quote, QuoteCreate, QuoteUpdate

router = APIRouter(prefix="/quotes", tags=["quotes"])

@router.get("/", response_model=list[Quote])
def list_quotes(db: Session = Depends(get_db)):
    """
    List an estimated price for ticket-related work, pending customer approval, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Quote records.
    """
    return quote_service.get_multi(db)

@router.get("/{id}", response_model=Quote)
def get_quote(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Quote record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Quote record.
    """
    return quote_service.get(db, id)

@router.post("/", response_model=Quote)
def create_quote(obj_in: QuoteCreate, db: Session = Depends(get_db)):
    """
    Create a new Quote record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Quote record.
    """
    return quote_service.create(db, obj_in)

@router.put("/{id}", response_model=Quote)
def update_quote(id: int, obj_in: QuoteUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Quote record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Quote record.
    """
    return quote_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_quote(id: int, db: Session = Depends(get_db)):
    """
    Delete a Quote record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return quote_service.delete(db, id)
