# ER-ServiceDesk/app/services/quote_email_service.py
# Service for emailing a quote to the customer.
"""
Sends a quote to a ticket's customer -- email-only, no print path.
Same design as app/services/waiver_service.py: the customer's
"I APPROVE" reply, if any, comes back as a normal Note on the ticket
through the existing inbound-email system, not tracked here. This
only tracks whether the quote itself was sent (Quote.quote_sent_at),
never whether it was answered.

Blocks sending an empty quote (no line items) -- a quote with nothing
on it and a $0.00 total would be confusing at best, and is almost
certainly a mistake, not something to actually email out.
"""

from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.quote import crud_quote
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.services.business_info_service import business_info_service
from app.services.audit_log_service import audit_log_service
from app.core.email import send_email, format_ticket_subject


def _format_line_items(line_items: list) -> str:
    """
    Args:
        line_items: The quote's QuoteLineItem rows.

    Returns:
        One "- Name xQty @ $unit = $line_total" line per item, joined
        by newlines. Deliberately not column-aligned -- a proportional
        email font would break any attempted alignment anyway, so a
        simple per-item line is more robust than a fragile table.
    """
    lines = []
    for item in line_items:
        name = item.service_name or item.part_name
        line_total = item.unit_price * item.quantity
        lines.append(f"- {name} x{item.quantity} @ ${item.unit_price} = ${line_total}")
    return "\n".join(lines)


class QuoteEmailService:
    """Builds and sends the quote email for a ticket's quote."""

    def send(self, db: Session, quote_id: int, current_user_id: int):
        """
        Emails this quote to its ticket's customer, and records when
        it was sent.

        Args:
            db: Active database session.
            quote_id: The quote to send.
            current_user_id: The user sending this -- recorded in the
                audit trail.

        Returns:
            The updated Quote instance, with quote_sent_at set.

        Raises:
            HTTPException: 404 if the quote, ticket, or customer
                doesn't exist. 400 if the quote has no line items, the
                customer has no email address on file, or the send
                itself fails.
        """
        quote = crud_quote.get(db, quote_id)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
        if not quote.line_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add at least one line item before sending this quote.")

        ticket = crud_ticket.get(db, quote.ticket_id)
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
            f"Here's your quote for the work on your device (Ticket #{ticket.id}):",
            "",
            _format_line_items(quote.line_items),
            "",
            f"Subtotal: ${quote.subtotal}",
        ]
        if quote.discount_amount and quote.discount_amount > 0:
            body_lines.append(f"Discount ({quote.discount_name}): -${quote.discount_amount}")
        if quote.tax_amount and quote.tax_amount > 0:
            body_lines.append(f"Tax ({quote.tax_rate_name}): ${quote.tax_amount}")
        body_lines.append(f"Total: ${quote.total}")
        body_lines.append("")
        body_lines.append(
            'This is an estimate, not a bill -- nothing is owed yet. '
            'If you\'d like to move forward, reply "I APPROVE" to this '
            'email to authorize the repairs. If you have any questions '
            'before deciding, just reply and let us know.'
        )

        body = "\n".join(body_lines)
        if info.business_name or info.business_phone:
            signature_parts = [p for p in (info.business_name, info.business_phone) if p]
            body = f"{body}\n\n{' -- '.join(signature_parts)}"

        business_name = info.business_name or "your repair shop"
        subject = format_ticket_subject(ticket.id, f"Your Quote from {business_name}")

        try:
            send_email(db, customer.email, subject, body)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Couldn't send the quote email: {e}")

        quote.quote_sent_at = datetime.now(UTC)
        db.commit()
        db.refresh(quote)

        audit_log_service.log(
            db, "quote_sent", "ticket", ticket.id, user_id=current_user_id,
            details=f"Quote #{quote.id} emailed to {customer.email}",
        )

        return quote

quote_email_service = QuoteEmailService()
