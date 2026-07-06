# ER-ServiceDesk/app/services/message_service.py
# Service layer for Message.
"""
Business logic for a customer-facing message exchanged on a ticket (e.g. via email).

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

import logging

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

        If the message is outbound, also sends it to the customer via
        Gmail SMTP after the record is saved. The Message record is the
        source of truth for the ticket's conversation history, so a send
        failure (bad credentials, network issue, etc.) is logged rather
        than raised -- the note still exists even if delivery didn't
        succeed, and a technician can see it and retry rather than losing
        the record entirely.

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
        a server log they'd never see. On failure, logs the full message
        content (not just IDs) so a tech can act on it immediately: retry
        the send, or call the customer directly and add an internal note
        that they did so.

        Args:
            db: Active database session.
            message: The already-created outbound Message instance.
        """
        ticket = crud_ticket.get(db, message.ticket_id)
        customer = crud_customer.get(db, message.customer_id)

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

    def update(self, db: Session, id: int, obj_in: MessageUpdate):
        """
        Update an existing Message using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Message instance.
        """
        db_obj = crud_message.get(db, id)
        return crud_message.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Message by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_message.delete(db, id)

message_service = MessageService()
