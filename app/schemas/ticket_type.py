# ER-ServiceDesk/app/schemas/ticket_type.py
# Pydantic schemas for TicketType entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning ticket type records within the ER‑ServiceDesk system.
# Ticket types represent specific classifications such as Bug Report,
# Feature Request, or General Inquiry, helping route and organize
# support tickets within the workflow.


from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class TicketTypeBase(BaseModel):
    name: str
    description: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class TicketTypeCreate(TicketTypeBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class TicketTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class TicketType(TicketTypeBase):
    id: int

    class Config:
        orm_mode = True