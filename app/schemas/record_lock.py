# ER-ServiceDesk/app/schemas/record_lock.py

"""
Request/response schemas for the check-out style record locking system.
"""

from datetime import datetime

from pydantic import BaseModel


class LockRequest(BaseModel):
    """Identifies which record a lock action applies to."""
    entity_type: str
    entity_id: int


class LockResult(BaseModel):
    """
    Response for a successful lock acquisition.

    Attributes:
        entity_type: The locked record's type.
        entity_id: The locked record's id.
        locked_by_user_id: Always the caller's own id on success --
            acquiring a lock only ever succeeds by taking it for
            yourself, never on someone else's behalf.
        locked_at: When the lock was acquired.
    """
    entity_type: str
    entity_id: int
    locked_by_user_id: int
    locked_at: datetime
