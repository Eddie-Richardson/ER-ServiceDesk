# ER-ServiceDesk/app/schemas/status_history.py
# Pydantic schemas for StatusHistory entities used to validate and structure an audit trail entry for a ticket status transition
"""
Pydantic schemas for StatusHistory entities used to validate and structure an audit trail entry for a ticket status transition.
"""

from datetime import datetime
from pydantic import BaseModel

class StatusHistoryBase(BaseModel):
    """Shared fields for StatusHistory across create/read/update."""
    ticket_id: int
    status_id: int
    changed_by: int

class StatusHistoryCreate(StatusHistoryBase):
    """Schema for creating a new StatusHistory record (client -> server)."""
    pass

class StatusHistoryUpdate(BaseModel):
    """Schema for partially updating an existing StatusHistory record. All fields optional."""
    ticket_id: int | None = None
    status_id: int | None = None
    changed_by: int | None = None

class StatusHistory(StatusHistoryBase):
    """Schema returned to the client for a StatusHistory record (server -> client)."""
    id: int
    changed_at: datetime
    class Config:
        orm_mode = True
