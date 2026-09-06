# ER-ServiceDesk/app/services/payment_email_service.py
"""
Sends a payment receipt automatically, the instant a payment is
recorded -- unlike the waiver/quote/invoice emails, this has no button
and no confirmation, since there's no real judgment call left: the
payment already happened, this just confirms it happened.

Deliberately never blocks payment recording. The payment is a real
financial event that already occurred; a receipt-email failure (bad
address, email not configured yet, etc.) must never prevent the
payment itself from being recorded. Failures are logged and swallowed,
the same pattern message_service.py already uses for outbound
ticket-reply emails -- not raised, unlike waiver/quote/invoice sending
where the email IS the entire point of the action.

A receipt is intentionally NOT a line-item breakdown of the invoice --
it only confirms the amount just paid, the running total paid so far,
and (if a balance remains) what's left. The full invoice with line
items is Invoice's own send action.

Three distinct shapes, chosen automatically each time based on actual
state, not on which code path called this:
  - Paid in full (whether via one direct payment, or the final
    installment completing a plan): a simple "paid in full" closing,
    no schedule, no due date -- this doubles as the final receipt.
  - The first payment ever linked to any installment of a payment
    plan: includes the FULL schedule (every installment, its due
    date, and whether it's paid), not just the next due date -- this
    doubles as confirmation the plan itself was set up correctly.
  - Any other partial payment (a plan's later installments, or a
    partial payment with no plan at all): the plain "remaining
    balance" line, plus next-due-date only if a plan exists.
"""

import logging
from decimal import Decimal
from sqlalchemy.orm import Session

from app.crud.invoice import crud_invoice
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.crud.payment import crud_payment
from app.services.business_info_service import business_info_service
from app.core.email import send_email, format_ticket_subject
from app.models.payment_plan import PaymentPlan
from app.models.payment_plan_installment import PaymentPlanInstallment

logger = logging.getLogger(__name__)


class PaymentEmailService:
    """Builds and sends the automatic payment receipt email."""

    def send_receipt(self, db: Session, payment):
        """
        Emails a receipt for a just-recorded payment. Never raises --
        any failure is logged and swallowed, so a real, successful
        payment recording is never undone or blocked by an email
        problem.

        Args:
            payment: The just-created Payment instance (already
                committed). If this payment is linked to a payment
                plan installment, that link must already be in place
                by the time this is called -- see
                payment_plan_service.record_installment_payment(),
                which calls this only after linking/redistribution is
                fully settled.
        """
        invoice = crud_invoice.get(db, payment.invoice_id)
        if not invoice:
            logger.error("FAILED TO SEND payment receipt: invoice_id=%s not found (payment_id=%s).", payment.invoice_id, payment.id)
            return

        ticket = crud_ticket.get(db, invoice.ticket_id)
        if not ticket:
            logger.error("FAILED TO SEND payment receipt: ticket_id=%s not found (invoice_id=%s).", invoice.ticket_id, invoice.id)
            return

        customer = crud_customer.get(db, ticket.customer_id)
        if not customer or not customer.email:
            logger.error("FAILED TO SEND payment receipt: no customer email on file (ticket_id=%s).", ticket.id)
            return

        try:
            total_paid = self._total_paid(db, invoice.id)
            remaining = invoice.total - total_paid

            body_lines = [
                f"Hi {customer.first_name},",
                "",
                f"We've received a payment of ${payment.amount} toward your invoice for Ticket #{ticket.id} (total: ${invoice.total}).",
                "",
            ]
            if remaining > 0:
                plan = self._plan_for_payment(db, payment.id)
                if plan and self._is_first_paid_installment_on_plan(db, plan.id, payment.id):
                    body_lines.append("Your payment plan has been set up as follows:")
                    body_lines.append(self._format_schedule(db, plan.id))
                    body_lines.append("")
                    body_lines.append(f"Remaining balance: ${remaining}")
                else:
                    body_lines.append(f"Remaining balance: ${remaining}")
                    next_due = self._next_installment_due_date(db, invoice.id)
                    if next_due:
                        body_lines.append(f"Next payment due: {next_due}.")
            else:
                body_lines.append("This invoice is now paid in full. Thank you!")

            body = "\n".join(body_lines)

            info = business_info_service.get_full(db)
            if info.business_name or info.business_phone:
                signature_parts = [p for p in (info.business_name, info.business_phone) if p]
                body = f"{body}\n\n{' -- '.join(signature_parts)}"

            business_name = info.business_name or "your repair shop"
            subject = format_ticket_subject(ticket.id, f"Payment Received -- {business_name}")

            send_email(db, customer.email, subject, body)
        except Exception:
            logger.exception(
                "FAILED TO SEND payment receipt for payment_id=%s (invoice_id=%s, ticket_id=%s). "
                "The payment itself was still recorded successfully -- a technician should confirm "
                "the customer got their receipt some other way if needed.",
                payment.id, invoice.id, ticket.id,
            )

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _total_paid(self, db: Session, invoice_id: int):
        payments = crud_payment.get_by_invoice(db, invoice_id)
        return sum((p.amount for p in payments), start=Decimal("0"))

    def _plan_for_payment(self, db: Session, payment_id: int):
        """
        Returns the PaymentPlan this payment is linked to via one of
        its installments, or None if this payment isn't tied to any
        installment at all (a plain, non-plan payment).
        """
        installment = db.query(PaymentPlanInstallment).filter_by(payment_id=payment_id).first()
        if not installment:
            return None
        return db.query(PaymentPlan).filter_by(id=installment.payment_plan_id).first()

    def _is_first_paid_installment_on_plan(self, db: Session, plan_id: int, payment_id: int) -> bool:
        """
        Args:
            payment_id: The payment just recorded -- excluded from the
                "any other paid installment" check, so this only ever
                looks at installments other than the one this payment
                itself just paid.

        Returns:
            True if no installment on this plan other than the one
            just paid by payment_id has ever been paid -- i.e. this is
            genuinely the plan's first payment, not just the first of
            this particular call.
        """
        other_paid_installment = (
            db.query(PaymentPlanInstallment)
            .filter(
                PaymentPlanInstallment.payment_plan_id == plan_id,
                PaymentPlanInstallment.payment_id.isnot(None),
                PaymentPlanInstallment.payment_id != payment_id,
            )
            .first()
        )
        return other_paid_installment is None

    def _format_schedule(self, db: Session, plan_id: int) -> str:
        """
        Returns one "- Installment N: $amount due YYYY-MM-DD [PAID]"
        line per installment, in sequence order, joined by newlines.
        [PAID] only appears on installments that already have a
        payment linked -- at the moment this is called for a plan's
        first payment, that's exactly the one just paid.
        """
        installments = (
            db.query(PaymentPlanInstallment)
            .filter_by(payment_plan_id=plan_id)
            .order_by(PaymentPlanInstallment.sequence_number.asc())
            .all()
        )
        lines = []
        for installment in installments:
            paid_marker = " [PAID]" if installment.payment_id is not None else ""
            lines.append(f"- Installment {installment.sequence_number}: ${installment.planned_amount} due {installment.due_date.isoformat()}{paid_marker}")
        return "\n".join(lines)

    def _next_installment_due_date(self, db: Session, invoice_id: int):
        """
        Returns the earliest unpaid installment's due_date as a
        string, or None if this invoice has no payment plan, or every
        installment is already paid.
        """
        plan = db.query(PaymentPlan).filter_by(invoice_id=invoice_id).first()
        if not plan:
            return None

        next_installment = (
            db.query(PaymentPlanInstallment)
            .filter_by(payment_plan_id=plan.id, payment_id=None)
            .order_by(PaymentPlanInstallment.sequence_number.asc())
            .first()
        )
        if not next_installment:
            return None

        return next_installment.due_date.isoformat()

payment_email_service = PaymentEmailService()
