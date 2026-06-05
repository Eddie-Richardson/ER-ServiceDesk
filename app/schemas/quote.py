# ER-ServiceDesk/app/schemas/quote.py
# Pydantic schemas for Quote entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning quote records within the ER‑ServiceDesk system.
# Quotes provide estimated pricing for ticket-related work and
# support approval workflows between agents and customers.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class QuoteBase(BaseModel):
    ticket_id: int
    amount: float
    details: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class QuoteCreate(QuoteBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class QuoteUpdate(BaseModel):
    ticket_id: int | None = None
    amount: float | None = None
    details: str | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Quote(QuoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
