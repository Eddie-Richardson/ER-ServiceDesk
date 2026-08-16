# ER-ServiceDesk/app/routes/payments.py
# API routes for Payment operations.
"""
REST endpoints for a payment applied against an invoice.

Gated on billing.manage, same reasoning as routes/quotes.py. Recording
a payment automatically updates the invoice's is_paid status -- see
payment_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.payment_service import payment_service
from app.services.payment_email_service import payment_email_service
from app.schemas.payment import Payment, PaymentCreate

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(require_permission("billing.manage"))])


@router.get("/", response_model=list[Payment])
def list_payments(invoice_id: int | None = None, db: Session = Depends(get_db)):
    """List payments, paginated, optionally filtered to a single invoice."""
    if invoice_id is not None:
        return payment_service.get_by_invoice(db, invoice_id)
    return payment_service.get_multi(db)


@router.get("/{id}", response_model=Payment)
def get_payment(id: int, db: Session = Depends(get_db)):
    """Fetch a single Payment record by ID."""
    return payment_service.get(db, id)


@router.post("/", response_model=Payment)
def create_payment(
    obj_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a new payment against an invoice. Automatically marks the invoice paid if this brings total payments up to its total."""
    new_payment = payment_service.create(db, obj_in, current_user.id)
    # Fired unconditionally, no confirmation -- unlike waiver/quote/
    # invoice sending, a payment receipt has no real judgment call
    # left, it just confirms something that already happened. Never
    # raises, so a receipt-email problem can never undo or block the
    # payment that was already, genuinely recorded above.
    payment_email_service.send_receipt(db, new_payment)
    return new_payment


@router.delete("/{id}")
def delete_payment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Payment by ID. Re-checks the invoice's paid status -- can un-mark a previously-paid invoice."""
    return payment_service.delete(db, id, current_user.id)
