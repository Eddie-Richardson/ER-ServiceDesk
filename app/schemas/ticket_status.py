# ER-ServiceDesk/app/schemas/ticket_statuses.py
# Pydantic schemas for TicketStatus entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning ticket status records within the ER‑ServiceDesk system.
# Statuses represent the various workflow states a ticket may occupy,
# such as Open, In Progress, or Resolved, and support UI display
# through optional color and description fields.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class TicketStatusBase(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class TicketStatusCreate(TicketStatusBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class TicketStatusUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class TicketStatus(TicketStatusBase):
    id: int

    class Config:
        orm_mode = True