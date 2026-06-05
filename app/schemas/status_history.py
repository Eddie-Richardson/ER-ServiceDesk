# ER-ServiceDesk/app/schemas/status_history.py
# Pydantic schemas for StatusHistory entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning status history records within the ER‑ServiceDesk system.
# Status history entries provide an immutable audit trail of ticket
# status transitions, including who performed the change and when.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class StatusHistoryBase(BaseModel):
    ticket_id: int
    status_id: int
    changed_by: int

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class StatusHistoryCreate(StatusHistoryBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class StatusHistoryUpdate(BaseModel):
    ticket_id: int | None = None
    status_id: int | None = None
    changed_by: int | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class StatusHistory(StatusHistoryBase):
    id: int
    changed_at: datetime

    class Config:
        orm_mode = True
