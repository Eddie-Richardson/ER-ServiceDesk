# ER-ServiceDesk/app/services/ticket_part_service.py
"""
Business logic for TicketPart operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

import logging

from sqlalchemy.orm import Session
from app.crud.ticket_part import crud_ticket_part
from app.schemas.ticket_part import TicketPartCreate, TicketPartUpdate
from app.workers.queue import get_queue
from app.workers.tasks import notify_customer_of_part_status_change
from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


class TicketPartService:
    """Business logic for TicketPart operations."""

    def get(self, db: Session, id: int):
        return crud_ticket_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_ticket_part.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        return crud_ticket_part.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: TicketPartCreate, current_user_id: int):
        """
        Note: creating a TicketPart does NOT trigger a customer
        notification, even if status is set to something other than
        "needed" on creation (e.g. bulk-importing existing tickets). Only
        a CHANGE in status, via update(), triggers the notify job --
        deliberately, so notifications only fire from real status
        transitions a tech takes action on, not from data entry.
        """
        new_ticket_part = crud_ticket_part.create(db, obj_in)
        audit_log_service.log(
            db, "ticket_part_created", "ticket", new_ticket_part.ticket_id, user_id=current_user_id,
            details=f"Added part id={new_ticket_part.part_id} to ticket",
        )
        return new_ticket_part

    def update(self, db: Session, id: int, obj_in: TicketPartUpdate, current_user_id: int):
        """
        If this update actually changes `status`, enqueues a background
        job (notify_customer_of_part_status_change) to notify the
        customer -- fired asynchronously via RQ so a slow/failed email
        send never delays or breaks this API response. The TicketPart
        update itself always succeeds regardless of what happens with
        that notification.

        Also sets ordered_at/received_at automatically the moment
        status genuinely transitions into "ordered"/"received" --
        always updated to the latest transition (e.g. a reorder after
        "delayed" genuinely moves ordered_at forward), not just set
        once and left alone.
        """
        db_obj = crud_ticket_part.get(db, id)
        previous_status = db_obj.status if db_obj else None
        update_data = obj_in.model_dump(exclude_unset=True)
        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_ticket_part.update(db, db_obj, obj_in)

        status_changed = previous_status is not None and updated.status != previous_status
        if status_changed:
            from datetime import datetime, UTC
            if updated.status == "ordered":
                updated.ordered_at = datetime.now(UTC)
                db.commit()
            elif updated.status == "received":
                updated.received_at = datetime.now(UTC)
                db.commit()

        if changed_fields:
            audit_log_service.log(
                db, "ticket_part_updated", "ticket", updated.ticket_id, user_id=current_user_id,
                details=f"Changed fields on part id={updated.part_id}: {', '.join(changed_fields)}",
            )

        if status_changed:
            try:
                get_queue().enqueue(notify_customer_of_part_status_change, updated.id)
            except Exception:
                # Redis being unavailable shouldn't break the actual
                # status update -- the tech's action (e.g. marking a
                # part "received") still needs to succeed even if the
                # notification can't be queued right now.
                logger.exception(
                    "Failed to enqueue notify_customer_of_part_status_change "
                    "for TicketPart id=%s (status %s -> %s). The status "
                    "change itself was saved; the customer was NOT notified.",
                    updated.id, previous_status, updated.status,
                )

        return updated

    def delete(self, db: Session, id: int):
        return crud_ticket_part.delete(db, id)

ticket_part_service = TicketPartService()
