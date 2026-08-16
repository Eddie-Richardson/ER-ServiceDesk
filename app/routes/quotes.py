# ER-ServiceDesk/app/routes/quotes.py
# API routes for Quote operations.
"""
REST endpoints for an estimated price for ticket-related work, pending
customer approval.

Gated on billing.manage -- the person doing billing, not necessarily a
superuser (Service/Discount/TaxRate catalog management, which sets
actual prices, stays superuser-only separately -- see
routes/services.py, routes/discounts.py, routes/tax_rates.py).

Thin HTTP layer: validates the request via the schema layer and
delegates all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.quote_service import quote_service
from app.services.quote_email_service import quote_email_service
from app.schemas.quote import Quote, QuoteCreate, QuoteUpdate
from app.schemas.quote_line_item import QuoteLineItem, QuoteLineItemUpdate
from app.schemas.invoice import Invoice as InvoiceSchema

router = APIRouter(prefix="/quotes", tags=["quotes"], dependencies=[Depends(require_permission("billing.manage"))])


@router.get("/", response_model=list[Quote])
def list_quotes(ticket_id: int | None = None, db: Session = Depends(get_db)):
    """List quotes, paginated, optionally filtered to a single ticket."""
    if ticket_id is not None:
        return quote_service.get_by_ticket(db, ticket_id)
    return quote_service.get_multi(db)


@router.get("/{id}", response_model=Quote)
def get_quote(id: int, db: Session = Depends(get_db)):
    """Fetch a single Quote record by ID, including its line items."""
    return quote_service.get(db, id)


@router.post("/", response_model=Quote)
def create_quote(
    obj_in: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Quote, starting with zero line items -- use the line-item endpoints below to build it up."""
    return quote_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=Quote)
def update_quote(
    id: int,
    obj_in: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a Quote's discount/tax selection or details. Changing discount/tax recalculates totals."""
    return quote_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_quote(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Quote by ID. Its own line items are cascade-deleted with it."""
    return quote_service.delete(db, id, current_user.id)


@router.post("/{quote_id}/line-items", response_model=QuoteLineItem)
def add_quote_line_item(
    quote_id: int,
    service_id: int | None = None,
    part_id: int | None = None,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adds a new line item to a quote -- exactly one of service_id/part_id -- snapshotting its current name/price, then recalculates totals."""
    return quote_service.add_line_item(db, quote_id, quantity, current_user.id, service_id=service_id, part_id=part_id)


@router.put("/line-items/{line_item_id}", response_model=QuoteLineItem)
def update_quote_line_item(
    line_item_id: int,
    obj_in: QuoteLineItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates a quote line item's quantity, then recalculates totals."""
    return quote_service.update_line_item(db, line_item_id, obj_in, current_user.id)


@router.delete("/line-items/{line_item_id}")
def remove_quote_line_item(
    line_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Removes a line item from a quote, then recalculates totals."""
    return quote_service.remove_line_item(db, line_item_id, current_user.id)


@router.post("/{quote_id}/convert-to-invoice", response_model=InvoiceSchema)
def convert_quote_to_invoice(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Converts an approved quote into a real Invoice -- copies its line items and discount/tax selection."""
    return quote_service.convert_to_invoice(db, quote_id, current_user.id)


@router.post("/{quote_id}/send", response_model=Quote)
def send_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Emails this quote to its ticket's customer, and records when it was sent. Rejects an empty quote (no line items)."""
    return quote_email_service.send(db, quote_id, current_user.id)
