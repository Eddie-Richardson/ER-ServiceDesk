# ER-ServiceDesk/app/services/status_history_service.py
# Service layer for StatusHistory -- read-only.
"""
Read-only business logic for a ticket's status change history.

No create/update/delete here -- entries are only ever written
internally by ticket_service.py (going straight to crud_status_history,
not through this service), whenever a ticket's status_id genuinely
changes. Keeping this service read-only matches the route layer (see
routes/status_histories.py) and keeps the audit trail's integrity
intact: nothing external can rewrite or erase history through this
layer.
"""

from sqlalchemy.orm import Session
from app.crud.status_history import crud_status_history

class StatusHistoryService:
    """Read-only business logic for StatusHistory."""

    def get(self, db: Session, id: int):
        """
        Fetch a single StatusHistory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching StatusHistory instance, or None if not found.
        """
        return crud_status_history.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of StatusHistory records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of StatusHistory instances.
        """
        return crud_status_history.get_multi(db, skip, limit)

status_history_service = StatusHistoryService()
