# ER-ServiceDesk/app/workers/tasks.py
# Background tasks run by the RQ worker.
"""
Background tasks executed asynchronously by the RQ worker process.
"""

import logging

from app.db.session import SessionLocal
from app.core.email import fetch_unread_emails
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.crud.ticket_part import crud_ticket_part
from app.schemas.message import MessageCreate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TicketPart status -> customer-facing message
# ---------------------------------------------------------------------------
# Maps a TicketPart.status value to a plain-English update for the
# customer. "needed" is intentionally absent -- it's the default status
# the moment a part requirement is first recorded, before anything has
# actually happened yet, so there's nothing worth telling the customer.
# Any status not in this map (including unrecognized/future values) is
# treated the same way: no notification, rather than guessing at wording.

_PART_STATUS_MESSAGES = {
    "ordered": "We've ordered the {part_name} needed for your repair.",
    "shipped": "The {part_name} for your repair has shipped.",
    "delayed": "There's a delay with the {part_name} for your repair.",
    "backordered": "The {part_name} for your repair is backordered.",
    "received": "The {part_name} for your repair has arrived at our shop.",
    "installed": "The {part_name} has been installed on your device.",
}

# Statuses where showing carrier/tracking info (if a tech has entered it)
# is actually useful to the customer -- no point attaching it to
# "received" or "installed", since the package has already arrived.
_SHOW_TRACKING_FOR_STATUSES = {"shipped", "delayed", "backordered"}


def build_part_status_message(ticket_part) -> str | None:
    """
    Build the customer-facing update text for a TicketPart's current
    status, or None if this status isn't customer-notable.

    Args:
        ticket_part: A TicketPart instance (with its `part` relationship
            loaded/loadable) whose CURRENT status should be described.

    Returns:
        The message body to send, or None if this status shouldn't
        trigger a customer notification at all.
    """
    template = _PART_STATUS_MESSAGES.get(ticket_part.status)
    if template is None:
        return None

    part_name = ticket_part.part.name if ticket_part.part else "part"
    message = template.format(part_name=part_name)

    if (
        ticket_part.status in _SHOW_TRACKING_FOR_STATUSES
        and ticket_part.carrier
        and ticket_part.tracking_number
    ):
        message += f" Carrier: {ticket_part.carrier}, Tracking #: {ticket_part.tracking_number}."

    return message


def notify_customer_of_part_status_change(ticket_part_id: int) -> None:
    """
    RQ job: when a TicketPart's status changes to something worth telling
    the customer about, create an outbound Message describing it.

    Enqueued by TicketPartService.update() whenever status actually
    changes -- not called directly from a request handler, since sending
    email shouldn't block the API response.

    Routes through message_service.create() (not crud_message directly)
    so this reuses the exact same Gmail-send + email_status-tracking
    logic that manually-created outbound messages already get -- a
    failure here is just as visible to a tech as any other failed send.

    Args:
        ticket_part_id: Primary key of the TicketPart whose status just
            changed.
    """
    # Imported here (not at module level) to avoid a circular import:
    # message_service imports from this same tasks module indirectly via
    # nothing today, but keeping the app.services import lazy here keeps
    # this task file safe to import from app.services without risk of
    # ever introducing one later.
    from app.services.message_service import message_service

    db = SessionLocal()
    try:
        ticket_part = crud_ticket_part.get(db, ticket_part_id)
        if not ticket_part:
            logger.error(
                "notify_customer_of_part_status_change: TicketPart id=%s "
                "not found -- it may have been deleted before this job ran.",
                ticket_part_id,
            )
            return

        content = build_part_status_message(ticket_part)
        if content is None:
            return

        ticket = crud_ticket.get(db, ticket_part.ticket_id)
        if not ticket:
            logger.error(
                "notify_customer_of_part_status_change: TicketPart id=%s "
                "references ticket_id=%s, which doesn't exist.",
                ticket_part_id, ticket_part.ticket_id,
            )
            return

        message_service.create(db, MessageCreate(
            ticket_id=ticket.id,
            customer_id=ticket.customer_id,
            direction="outbound",
            content=content,
        ))
    finally:
        db.close()


def poll_inbound_email() -> dict:
    """
    Check the Gmail inbox for unread customer replies and thread each one
    onto its ticket as a new inbound Message.

    Meant to be enqueued on a recurring schedule (e.g. every minute) via
    rq-scheduler -- see app/workers/scheduler.py -- not called directly
    from a request handler.

    Matching an email to a ticket requires BOTH of:
      - A "[Ticket #N]" marker in the subject line (present because our
        own outbound messages include it, and most mail clients preserve
        it through Reply)
      - A Customer record whose email matches the sender address

    Either one failing means the message can't be safely attributed, so
    it's left as unread in the inbox (not marked seen, not silently
    dropped) and logged for manual triage -- a tech can search the inbox
    directly and re-associate it by hand.

    Returns:
        A summary dict: {"processed": int, "unmatched": int} -- mostly
        useful for tests and for eyeballing the RQ job result in the
        dashboard/logs.
    """
    from app.crud.message import crud_message

    processed = 0
    unmatched = 0

    db = SessionLocal()
    try:
        for inbound in fetch_unread_emails():
            if inbound.ticket_id is None:
                logger.warning(
                    "Unmatched inbound email from %s (subject=%r): no "
                    "[Ticket #N] marker found in subject. Needs manual "
                    "triage -- left as unread in the inbox.",
                    inbound.from_address, inbound.subject,
                )
                unmatched += 1
                continue

            ticket = crud_ticket.get(db, inbound.ticket_id)
            if not ticket:
                logger.warning(
                    "Inbound email from %s references ticket #%s, which "
                    "doesn't exist. Needs manual triage.",
                    inbound.from_address, inbound.ticket_id,
                )
                unmatched += 1
                continue

            customer = crud_customer.get_by_email(db, inbound.from_address)
            if not customer:
                logger.warning(
                    "Inbound email for ticket #%s came from %s, which "
                    "doesn't match any Customer record. Needs manual "
                    "triage.",
                    inbound.ticket_id, inbound.from_address,
                )
                unmatched += 1
                continue

            crud_message.create(db, MessageCreate(
                ticket_id=ticket.id,
                customer_id=customer.id,
                direction="inbound",
                content=inbound.body,
            ))
            processed += 1
    finally:
        db.close()

    return {"processed": processed, "unmatched": unmatched}
