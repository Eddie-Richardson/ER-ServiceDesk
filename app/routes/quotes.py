# ER-ServiceDesk/app/routes/quotes.py
# API routes for Quote operations.
#
# Exposes REST endpoints for interacting with Quote records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.quote_service import quote_service
from app.schemas.quote import Quote, QuoteCreate, QuoteUpdate

router = APIRouter(prefix="/quotes", tags=["quotes"])

@router.get("/", response_model=list[Quote])
def list_quotes(db: Session = Depends(get_db)):
    """
    Returns a list of Quote records.
    """
    return quote_service.get_multi(db)

@router.get("/{id}", response_model=Quote)
def get_quote(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Quote record by ID.
    """
    return quote_service.get(db, id)

@router.post("/", response_model=Quote)
def create_quote(obj_in: QuoteCreate, db: Session = Depends(get_db)):
    """
    Creates a new Quote record.
    """
    return quote_service.create(db, obj_in)

@router.put("/{id}", response_model=Quote)
def update_quote(id: int, obj_in: QuoteUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Quote record.
    """
    return quote_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_quote(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Quote record by ID.
    """
    return quote_service.delete(db, id)
