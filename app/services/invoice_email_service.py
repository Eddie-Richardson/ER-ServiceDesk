# ER-ServiceDesk/app/services/invoice_email_service.py
"""
Sends an invoice to a ticket's customer -- email-only, no print path.
Same design as app/services/quote_email_service.py, with one real
difference: unlike a quote, an invoice is sendable even after
is_paid is true -- re-sending a paid invoice serves as a receipt, not
blocked. The email body itself reflects paid vs unpaid status with a
different closing line.

Blocks sending an empty invoice (no line items), same reasoning as
quotes -- a $0.00 bill is almost certainly a mistake.
"""

from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.invoice import crud_invoice
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.services.business_info_service import business_info_service
from app.services.audit_log_service import audit_log_service
from app.core.email import send_email, format_ticket_subject


def _format_line_items(line_items: list) -> str:
    """
    Returns one "- Name xQty @ $unit = $line_total" line per item,
    joined by newlines. Same format as quote_email_service's own line
    items, for consistency between the two email types.
    """
    lines = []
    for item in line_items:
        name = item.service_name or item.part_name
        line_total = item.unit_price * item.quantity
        lines.append(f"- {name} x{item.quantity} @ ${item.unit_price} = ${line_total}")
    return "\n".join(lines)


class InvoiceEmailService:
    """Builds and sends the invoice email for a ticket's invoice."""

    def send(self, db: Session, invoice_id: int, current_user_id: int):
        """
        Emails this invoice to its ticket's customer, and records when
        it was sent. Sendable regardless of is_paid -- a paid invoice
        being re-sent serves as a receipt.

        Args:
            current_user_id: The user sending this -- recorded in the
                audit trail.

        Returns:
            The updated Invoice instance, with invoice_sent_at set.

        Raises:
            HTTPException: 404 if the invoice, ticket, or customer
                doesn't exist. 400 if the invoice has no line items,
                the customer has no email address on file, or the
                send itself fails.
        """
        invoice = crud_invoice.get(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        if not invoice.line_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add at least one line item before sending this invoice.")

        ticket = crud_ticket.get(db, invoice.ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        customer = crud_customer.get(db, ticket.customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        if not customer.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This customer has no email address on file.")

        info = business_info_service.get_full(db)

        body_lines = [
            f"Hi {customer.first_name},",
            "",
            f"Here's your invoice for the completed work on your device (Ticket #{ticket.id}):",
            "",
            _format_line_items(invoice.line_items),
            "",
            f"Subtotal: ${invoice.subtotal}",
        ]
        if invoice.discount_amount and invoice.discount_amount > 0:
            body_lines.append(f"Discount ({invoice.discount_name}): -${invoice.discount_amount}")
        if invoice.tax_amount and invoice.tax_amount > 0:
            body_lines.append(f"Tax ({invoice.tax_rate_name}): ${invoice.tax_amount}")
        body_lines.append(f"Total: ${invoice.total}")
        body_lines.append("")
        if invoice.is_paid:
            body_lines.append("This invoice has been paid in full. Thank you for your business!")
        else:
            body_lines.append("Payment is due upon completion. Reply to this email or contact us to arrange payment.")

        body = "\n".join(body_lines)
        if info.business_name or info.business_phone:
            signature_parts = [p for p in (info.business_name, info.business_phone) if p]
            body = f"{body}\n\n{' -- '.join(signature_parts)}"

        business_name = info.business_name or "your repair shop"
        subject = format_ticket_subject(ticket.id, f"Your Invoice from {business_name}")

        try:
            send_email(db, customer.email, subject, body)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Couldn't send the invoice email: {e}")

        invoice.invoice_sent_at = datetime.now(UTC)
        db.commit()
        db.refresh(invoice)

        audit_log_service.log(
            db, "invoice_sent", "ticket", ticket.id, user_id=current_user_id,
            details=f"Invoice #{invoice.id} emailed to {customer.email}",
        )

        return invoice

invoice_email_service = InvoiceEmailService()
