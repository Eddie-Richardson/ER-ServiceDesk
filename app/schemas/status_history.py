# ER-ServiceDesk/app/schemas/status_history.py
"""
Request/response schemas for an audit trail entry for a ticket status
transition.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class StatusHistoryBase(BaseModel):
    """Shared fields for StatusHistory across create/read/update."""
    ticket_id: int
    status_id: int
    changed_by: int

class StatusHistoryCreate(StatusHistoryBase):
    """Schema for creating a new StatusHistory record (client -> server)."""
    pass

class StatusHistory(StatusHistoryBase):
    """Schema returned to the client for a StatusHistory record (server -> client)."""
    id: int
    changed_at: datetime
    status_name: str | None = None
    changed_by_name: str | None = None
    model_config = ConfigDict(from_attributes=True)
