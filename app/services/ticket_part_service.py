# ER-ServiceDesk/app/services/ticket_part_service.py
# Service layer for TicketPart.
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

logger = logging.getLogger(__name__)


class TicketPartService:
    """Business logic for TicketPart operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single TicketPart by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TicketPart instance, or None if not found.
        """
        return crud_ticket_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of TicketPart records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TicketPart instances.
        """
        return crud_ticket_part.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        """
        Fetch every part requirement attached to a given ticket.

        Args:
            db: Active database session.
            ticket_id: The ticket to look up part requirements for.

        Returns:
            A list of TicketPart instances for that ticket.
        """
        return crud_ticket_part.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: TicketPartCreate):
        """
        Create a new TicketPart using validated input data.

        Note: creating a TicketPart does NOT trigger a customer
        notification, even if status is set to something other than
        "needed" on creation (e.g. bulk-importing existing tickets). Only
        a CHANGE in status, via update(), triggers the notify job --
        deliberately, so notifications only fire from real status
        transitions a tech takes action on, not from data entry.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created TicketPart instance.
        """
        return crud_ticket_part.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketPartUpdate):
        """
        Update an existing TicketPart using validated input data.

        If this update actually changes `status`, enqueues a background
        job (notify_customer_of_part_status_change) to notify the
        customer -- fired asynchronously via RQ so a slow/failed email
        send never delays or breaks this API response. The TicketPart
        update itself always succeeds regardless of what happens with
        that notification.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated TicketPart instance.
        """
        db_obj = crud_ticket_part.get(db, id)
        previous_status = db_obj.status if db_obj else None

        updated = crud_ticket_part.update(db, db_obj, obj_in)

        if previous_status is not None and updated.status != previous_status:
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
        """
        Delete a TicketPart by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket_part.delete(db, id)

ticket_part_service = TicketPartService()
