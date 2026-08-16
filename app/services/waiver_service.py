# ER-ServiceDesk/app/services/waiver_service.py
# Service for sending the liability waiver email.
"""
Sends the liability waiver to a ticket's customer -- email-only, no
print/signature path. The customer's "I AGREE" reply, if any, comes
back as a normal Note on the ticket through the existing inbound-email
system, the same way any other customer reply does -- that reply IS
the consent record, nothing else is tracked as a signature.

This only tracks whether the request itself was sent
(Ticket.waiver_sent_at), never whether it was answered -- answering
shows up in the ticket's own notes/timeline like any other message.
"""

from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.services.business_info_service import business_info_service
from app.services.audit_log_service import audit_log_service
from app.core.email import send_email, format_ticket_subject

_WAIVER_BODY_TEMPLATE = """Computer Repair & Service Waiver

I authorize {business_name} to perform work on my computer. I understand that {business_name} is not an authorized service dealer. I agree to release, indemnify, and hold harmless {business_name} from liability for any claims for damages of any kind or description that may arise from any diagnosis, repair, installation, or maintenance services performed on my computer, unless caused by gross negligence. I understand that {business_name} is not responsible for any data loss that may occur as a result of work done on my computer.

Estimated Completion Time: An estimated completion time will be provided up front. Unforeseen circumstances may affect the ability to complete repair(s) as estimated.

Hardware Replacement: If replacement parts are needed, {business_name} will obtain them only with my authorization, and I am responsible for their cost. Old parts will be returned to me upon completion.

Impact of Upgrades: I understand it's my responsibility to know the impact of OS/software upgrades, which can cause incompatibilities and possible data loss.

Payment: Fees are due upon completion. Unpaid accounts are subject to collection. A deposit may be required, or the computer held until paid in full.

Privacy: {business_name} will not browse your hard drive, but may inadvertently see data during the course of work.

Right to Refuse: {business_name} may refuse work at its sole discretion.

Abandonment: Equipment not picked up within 90 days of notification of completion is treated as abandoned property.

By replying "I AGREE" to this email, I confirm that I am the true owner of this device, understand this waiver may void manufacturer warranties, understand no warranty is offered on technical support performed, and waive claims for incidental damages except where due to gross negligence."""


class WaiverService:
    """Builds and sends the liability waiver email for a ticket."""

    def send(self, db: Session, ticket_id: int, current_user_id: int):
        """
        Sends the liability waiver email to the ticket's customer, and
        records when it was sent.

        Args:
            db: Active database session.
            ticket_id: The ticket to send the waiver for.
            current_user_id: The user sending this -- recorded in the
                audit trail.

        Returns:
            The updated Ticket instance, with waiver_sent_at set.

        Raises:
            HTTPException: 404 if the ticket or its customer doesn't
                exist. 400 if the customer has no email address on
                file, or if the send itself fails (matching how a
                failed email is handled elsewhere -- surfaced clearly,
                not silently swallowed).
        """
        ticket = crud_ticket.get(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        customer = crud_customer.get(db, ticket.customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        if not customer.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This customer has no email address on file.")

        info = business_info_service.get_full(db)
        business_name = info.business_name or "the shop"

        body = _WAIVER_BODY_TEMPLATE.format(business_name=business_name)
        if info.business_name or info.business_phone:
            signature_parts = [p for p in (info.business_name, info.business_phone) if p]
            body = f"{body}\n\n{' -- '.join(signature_parts)}"

        subject = format_ticket_subject(ticket.id, "Liability Waiver -- Please Reply to Confirm")

        try:
            send_email(db, customer.email, subject, body)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Couldn't send the waiver email: {e}")

        ticket.waiver_sent_at = datetime.now(UTC)
        db.commit()
        db.refresh(ticket)

        audit_log_service.log(
            db, "waiver_sent", "ticket", ticket.id, user_id=current_user_id,
            details=f"Liability waiver emailed to {customer.email}",
        )

        return ticket

waiver_service = WaiverService()
