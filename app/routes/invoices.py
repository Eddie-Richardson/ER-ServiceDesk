# ER-ServiceDesk/app/routes/invoices.py
# API routes for Invoice operations.
"""
REST endpoints for a bill generated for work performed on a ticket.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.invoice_service import invoice_service
from app.schemas.invoice import Invoice, InvoiceCreate, InvoiceUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Invoice])
def list_invoices(db: Session = Depends(get_db)):
    """
    List a bill generated for work performed on a ticket, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Invoice records.
    """
    return invoice_service.get_multi(db)

@router.get("/{id}", response_model=Invoice)
def get_invoice(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Invoice record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Invoice record.
    """
    return invoice_service.get(db, id)

@router.post("/", response_model=Invoice)
def create_invoice(obj_in: InvoiceCreate, db: Session = Depends(get_db)):
    """
    Create a new Invoice record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Invoice record.
    """
    return invoice_service.create(db, obj_in)

@router.put("/{id}", response_model=Invoice)
def update_invoice(id: int, obj_in: InvoiceUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Invoice record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Invoice record.
    """
    return invoice_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_invoice(id: int, db: Session = Depends(get_db)):
    """
    Delete a Invoice record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return invoice_service.delete(db, id)
