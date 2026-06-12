# ER-ServiceDesk/app/schemas/invoices.py
# Pydantic schemas for Invoice entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning invoice records within the ER‑ServiceDesk system.
# They support billing workflows, payment tracking, and ticket‑linked
# financial operations.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class InvoiceBase(BaseModel):
    ticket_id: int
    amount: float
    details: str | None = None
    is_paid: bool

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class InvoiceCreate(InvoiceBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class InvoiceUpdate(BaseModel):
    ticket_id: int | None = None
    amount: float | None = None
    details: str | None = None
    is_paid: bool | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Invoice(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
