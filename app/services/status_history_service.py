# ER-ServiceDesk/app/services/status_history_service.py
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
        return crud_status_history.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 500, ticket_id: int | None = None):
        return crud_status_history.get_multi(db, skip, limit, ticket_id)

status_history_service = StatusHistoryService()
