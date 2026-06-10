# ER-ServiceDesk/app/schemas/ticket.py
# Pydantic schemas for Ticket entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning ticket records within the ER‑ServiceDesk system.
# Tickets serve as the core workflow entity, linking customers,
# devices, categories, types, statuses, and assigned technicians.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class TicketBase(BaseModel):
    customer_id: int
    device_id: int
    category_id: int
    type_id: int
    status_id: int
    assigned_to: int | None = None
    title: str
    description: str | None = None
    priority: str

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class TicketCreate(TicketBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class TicketUpdate(BaseModel):
    customer_id: int | None = None
    device_id: int | None = None
    category_id: int | None = None
    type_id: int | None = None
    status_id: int | None = None
    assigned_to: int | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Ticket(TicketBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True