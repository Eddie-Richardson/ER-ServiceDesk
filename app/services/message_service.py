# ER-ServiceDesk/app/services/message_service.py
# Service layer for Message.
"""
Business logic for a ticket's full note/conversation history --
internal notes and customer-facing email exchange, unified into one
system. Originally split across two overlapping models (Note and
Message); merged into this one after that overlap was called out
directly.

Coordinates CRUD operations and is where entity-specific rules live.
Route handlers call into this layer rather than the CRUD layer
directly, so business rules stay in one place.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.message import crud_message
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.schemas.message import MessageCreate, MessageUpdate
from app.core.email import send_email, format_ticket_subject

logger = logging.getLogger(__name__)


class MessageService:
    """Business logic for Message operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Message by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Message instance, or None if not found.
        """
        return crud_message.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Message records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Message instances.
        """
        return crud_message.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: MessageCreate):
        """
        Create a new Message using validated input data.

        If direction is "outbound", also sends it to the customer via
        SMTP after the record is saved. "internal" entries are never
        emailed -- staff-only by design. "inbound" entries (the
        customer's own reply) are created by the inbound-email polling
        worker, not through this path in normal use, but the same
        create() logic applies regardless of caller.

        A send failure (bad credentials, network issue, etc.) is
        logged rather than raised -- the entry still exists even if
        delivery didn't succeed, and a technician can see it and retry
        rather than losing the record entirely.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Message instance.
        """
        message = crud_message.create(db, obj_in)

        if message.direction == "outbound":
            self._send_outbound(db, message)

        return message

    def _send_outbound(self, db: Session, message) -> None:
        """
        Send an outbound Message to its customer via email, and record
        whether it succeeded.

        Sets message.email_status to "sent" or "failed" so a failure is
        visible to a tech looking at the ticket in the app -- not just in
        a server log they'd never see.

        Args:
            db: Active database session.
            message: The already-created outbound Message instance.
        """
        ticket = crud_ticket.get(db, message.ticket_id)
        customer = crud_customer.get(db, message.customer_id) if message.customer_id else None

        if not ticket or not customer:
            logger.error(
                "FAILED TO SEND Message id=%s: ticket or customer not found "
                "(ticket_id=%s, customer_id=%s). Message content: %r",
                message.id, message.ticket_id, message.customer_id, message.content,
            )
            message.email_status = "failed"
            db.commit()
            return

        subject = format_ticket_subject(ticket.id, ticket.title)

        try:
            send_email(customer.email, subject, message.content)
        except Exception:
            logger.exception(
                "FAILED TO SEND Message id=%s (ticket_id=%s) to customer %s. "
                "A technician should retry this send or call the customer "
                "directly and log an internal note confirming they did. "
                "Message content: %r",
                message.id, message.ticket_id, customer.email, message.content,
            )
            message.email_status = "failed"
        else:
            message.email_status = "sent"

        db.commit()

    def update(self, db: Session, id: int, obj_in: MessageUpdate, current_user):
        """
        Edit an existing Message's content.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: The new content (see MessageUpdate -- deliberately
                the only field an edit can change).
            current_user: The authenticated user making this request.

        Returns:
            The updated Message instance.

        Raises:
            HTTPException: 403 if not allowed. Internal/outbound
                entries (staff-authored) can only be edited by their
                own author or a superuser. Inbound entries (the
                customer's own reply) have no staff author to defer
                to, so only a superuser may touch one at all.
        """
        db_obj = crud_message.get(db, id)
        if db_obj.user_id is not None:
            if db_obj.user_id != current_user.id and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the entry's own author or an admin can edit it.",
                )
        elif not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can edit a customer's own message.",
            )
        return crud_message.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int, current_user):
        """
        Delete a Message by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user: The authenticated user making this request.

        Raises:
            HTTPException: 403 if not allowed -- same reasoning as update().
        """
        db_obj = crud_message.get(db, id)
        if db_obj.user_id is not None:
            if db_obj.user_id != current_user.id and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the entry's own author or an admin can delete it.",
                )
        elif not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can delete a customer's own message.",
            )
        return crud_message.delete(db, id)

message_service = MessageService()
