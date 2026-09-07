# ER-ServiceDesk/app/services/note_service.py
"""
Business logic for a ticket's full note/conversation history --
internal notes and customer-facing email exchange, unified into one
system.

Coordinates CRUD operations and is where entity-specific rules live.
Route handlers call into this layer rather than the CRUD layer
directly, so business rules stay in one place.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.note import crud_note
from app.crud.ticket import crud_ticket
from app.crud.customer import crud_customer
from app.schemas.note import NoteCreate, NoteUpdate
from app.core.email import send_email, format_ticket_subject
from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


class NoteService:
    """Business logic for Note operations."""

    def get(self, db: Session, id: int):
        return crud_note.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 500, ticket_id: int | None = None):
        return crud_note.get_multi(db, skip, limit, ticket_id)

    def create(self, db: Session, obj_in: NoteCreate):
        """
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
        """
        note = crud_note.create(db, obj_in)

        if note.direction == "outbound":
            self._send_outbound(db, note)

        return note

    def _send_outbound(self, db: Session, note) -> None:
        """
        Sets note.email_status to "sent" or "failed" so a failure is
        visible to a tech looking at the ticket in the app -- not just in
        a server log they'd never see.
        """
        ticket = crud_ticket.get(db, note.ticket_id)
        customer = crud_customer.get(db, note.customer_id) if note.customer_id else None

        if not ticket or not customer:
            logger.error(
                "FAILED TO SEND Note id=%s: ticket or customer not found "
                "(ticket_id=%s, customer_id=%s). Note content: %r",
                note.id, note.ticket_id, note.customer_id, note.content,
            )
            note.email_status = "failed"
            db.commit()
            audit_log_service.log(
                db, "outbound_notification_failed", "ticket", note.ticket_id, user_id=note.user_id,
                details="Ticket or customer not found",
            )
            return

        subject = format_ticket_subject(ticket.id, ticket.title)

        try:
            send_email(db, customer.email, subject, note.content)
        except Exception:
            logger.exception(
                "FAILED TO SEND Note id=%s (ticket_id=%s) to customer %s. "
                "A technician should retry this send or call the customer "
                "directly and log an internal note confirming they did. "
                "Note content: %r",
                note.id, note.ticket_id, customer.email, note.content,
            )
            note.email_status = "failed"
        else:
            note.email_status = "sent"

        db.commit()

        audit_log_service.log(
            db,
            "outbound_notification_sent" if note.email_status == "sent" else "outbound_notification_failed",
            "ticket", note.ticket_id, user_id=note.user_id,
            details=f"Sent to {customer.email}" if note.email_status == "sent" else f"Delivery failed to {customer.email}",
        )

    def update(self, db: Session, id: int, obj_in: NoteUpdate, current_user):
        """
        Args:
            obj_in: The new content (see NoteUpdate -- deliberately
                the only field an edit can change).

        Raises:
            HTTPException: 403 if not allowed. Internal/outbound
                entries (staff-authored) can only be edited by their
                own author or a superuser. Inbound entries (the
                customer's own reply) have no staff author to defer
                to, so only a superuser may touch one at all.
        """
        db_obj = crud_note.get(db, id)
        if db_obj.user_id is not None:
            if db_obj.user_id != current_user.id and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the entry's own author or an admin can edit it.",
                )
        elif not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can edit a customer's own note.",
            )
        return crud_note.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int, current_user):
        """
        Raises:
            HTTPException: 403 if not allowed -- same reasoning as update().
        """
        db_obj = crud_note.get(db, id)
        if db_obj.user_id is not None:
            if db_obj.user_id != current_user.id and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the entry's own author or an admin can delete it.",
                )
        elif not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can delete a customer's own note.",
            )
        return crud_note.delete(db, id)

note_service = NoteService()
