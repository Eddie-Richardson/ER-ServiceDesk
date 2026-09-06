# ER-ServiceDesk/app/routes/invoices.py
"""
REST endpoints for a bill generated for work performed on a ticket.

Gated on billing.manage, same reasoning as routes/quotes.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.invoice_service import invoice_service
from app.services.invoice_email_service import invoice_email_service
from app.schemas.invoice import Invoice, InvoiceCreate, InvoiceUpdate
from app.schemas.invoice_line_item import InvoiceLineItem, InvoiceLineItemUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(require_permission("billing.manage"))])


@router.get("/", response_model=list[Invoice])
def list_invoices(ticket_id: int | None = None, db: Session = Depends(get_db)):
    """List invoices, paginated, optionally filtered to a single ticket."""
    if ticket_id is not None:
        return invoice_service.get_by_ticket(db, ticket_id)
    return invoice_service.get_multi(db)


@router.get("/{id}", response_model=Invoice)
def get_invoice(id: int, db: Session = Depends(get_db)):
    """Fetch a single Invoice record by ID, including its line items."""
    invoice = invoice_service.get(db, id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/", response_model=Invoice)
def create_invoice(
    obj_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Invoice directly (not via quote conversion -- see POST /quotes/{id}/convert-to-invoice for that path)."""
    return invoice_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=Invoice)
def update_invoice(
    id: int,
    obj_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an Invoice's discount/tax selection, details, or is_paid. Changing discount/tax recalculates totals."""
    return invoice_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes an empty, never-sent, unpaid, non-converted invoice -- only if it's the most recently created one."""
    return invoice_service.delete(db, id, current_user.id)


@router.post("/{invoice_id}/line-items", response_model=InvoiceLineItem)
def add_invoice_line_item(
    invoice_id: int,
    service_id: int | None = None,
    part_id: int | None = None,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adds a new line item to an invoice -- exactly one of service_id/part_id -- snapshotting its current name/price, then recalculates totals. A part line item deducts real inventory."""
    return invoice_service.add_line_item(db, invoice_id, quantity, current_user.id, service_id=service_id, part_id=part_id)


@router.put("/line-items/{line_item_id}", response_model=InvoiceLineItem)
def update_invoice_line_item(
    line_item_id: int,
    obj_in: InvoiceLineItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates an invoice line item's quantity, then recalculates totals."""
    return invoice_service.update_line_item(db, line_item_id, obj_in, current_user.id)


@router.delete("/line-items/{line_item_id}")
def remove_invoice_line_item(
    line_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Removes a line item from an invoice, then recalculates totals."""
    return invoice_service.remove_line_item(db, line_item_id, current_user.id)


@router.post("/{invoice_id}/send", response_model=Invoice)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Emails this invoice to its ticket's customer, and records when it was sent. Rejects an empty invoice (no line items). Sendable even after is_paid -- serves as a receipt."""
    return invoice_email_service.send(db, invoice_id, current_user.id)
