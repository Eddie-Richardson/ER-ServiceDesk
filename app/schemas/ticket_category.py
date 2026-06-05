# ER-ServiceDesk/app/schemas/ticket_category.py
# Pydantic schemas for TicketCategory entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning ticket category records within the ER‑ServiceDesk system.
# Categories represent high‑level groupings used to organize and route
# support tickets across teams and workflows.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class TicketCategoryBase(BaseModel):
    name: str
    description: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class TicketCategoryCreate(TicketCategoryBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class TicketCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class TicketCategory(TicketCategoryBase):
    id: int

    class Config:
        orm_mode = True