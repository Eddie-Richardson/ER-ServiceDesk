# ER-ServiceDesk/app/services/payment_service.py
"""
Business logic for a payment applied against an invoice.

Recording a payment automatically marks the invoice as paid once total
payments received meet or exceed its total -- not something set
directly on the invoice itself.
"""

from decimal import Decimal

from sqlalchemy.orm import Session
from app.crud.payment import crud_payment
from app.crud.invoice import crud_invoice
from app.schemas.payment import PaymentCreate
from app.services.audit_log_service import audit_log_service


class PaymentService:
    """Business logic for Payment operations, including auto-updating an invoice's paid status."""

    def get(self, db: Session, id: int):
        return crud_payment.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_payment.get_multi(db, skip, limit)

    def get_by_invoice(self, db: Session, invoice_id: int):
        return crud_payment.get_by_invoice(db, invoice_id)

    def create(self, db: Session, obj_in: PaymentCreate, current_user_id: int):
        new_payment = crud_payment.create(db, obj_in)

        invoice = crud_invoice.get(db, obj_in.invoice_id)
        if invoice:
            self._refresh_paid_status(db, invoice)

            audit_log_service.log(
                db, "payment_recorded", "ticket", invoice.ticket_id, user_id=current_user_id,
                details=f"Recorded ${new_payment.amount} payment ({new_payment.method}) on Invoice #{invoice.id}",
            )

        # Deliberately NOT sending the payment receipt here. A caller
        # that links this payment to a payment-plan installment (see
        # payment_plan_service.record_installment_payment()) needs
        # that linking -- and any resulting redistribution -- fully
        # settled BEFORE the receipt's "next payment due" lookup runs,
        # or it would find the just-paid installment still showing as
        # unpaid and report the wrong due date. Each real caller of
        # this method sends the receipt itself, at the point where its
        # own state is actually final.
        return new_payment

    def delete(self, db: Session, id: int, current_user_id: int):
        """Re-checks the invoice's paid status after deleting -- removing a payment can un-mark a previously-paid invoice."""
        db_obj = crud_payment.get(db, id)
        invoice_id = db_obj.invoice_id if db_obj else None

        result = crud_payment.delete(db, id)

        if invoice_id is not None:
            invoice = crud_invoice.get(db, invoice_id)
            if invoice:
                self._refresh_paid_status(db, invoice)

                audit_log_service.log(
                    db, "payment_deleted", "ticket", invoice.ticket_id, user_id=current_user_id,
                    details=f"Deleted payment #{id} from Invoice #{invoice_id}",
                )

        return result

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _refresh_paid_status(self, db: Session, invoice):
        """
        Recomputes total payments against this invoice and updates
        is_paid to match -- True if total payments meet or exceed the
        invoice's total, False otherwise (covers a payment being
        edited down or deleted un-marking a previously-paid invoice).
        """
        payments = crud_payment.get_by_invoice(db, invoice.id)
        total_paid = sum((p.amount for p in payments), start=Decimal("0"))
        is_paid_now = total_paid >= invoice.total
        if is_paid_now != invoice.is_paid:
            invoice.is_paid = is_paid_now
            db.commit()

payment_service = PaymentService()
