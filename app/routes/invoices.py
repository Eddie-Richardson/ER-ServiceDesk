# ER-ServiceDesk/app/routes/invoices.py
# API routes for Invoice operations.
#
# Exposes REST endpoints for interacting with Invoice records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.invoice_service import invoice_service
from app.schemas.invoice import Invoice, InvoiceCreate, InvoiceUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("/", response_model=list[Invoice])
def list_invoices(db: Session = Depends(get_db)):
    """
    Returns a list of Invoice records.
    """
    return invoice_service.get_multi(db)

@router.get("/{id}", response_model=Invoice)
def get_invoice(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Invoice record by ID.
    """
    return invoice_service.get(db, id)

@router.post("/", response_model=Invoice)
def create_invoice(obj_in: InvoiceCreate, db: Session = Depends(get_db)):
    """
    Creates a new Invoice record.
    """
    return invoice_service.create(db, obj_in)

@router.put("/{id}", response_model=Invoice)
def update_invoice(id: int, obj_in: InvoiceUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Invoice record.
    """
    return invoice_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_invoice(id: int, db: Session = Depends(get_db)):
    """
    Deletes an Invoice record by ID.
    """
    return invoice_service.delete(db, id)
