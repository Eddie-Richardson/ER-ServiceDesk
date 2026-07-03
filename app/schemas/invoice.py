# ER-ServiceDesk/app/schemas/invoice.py
# Pydantic schemas for Invoice entities used to validate and structure a bill generated for work performed on a ticket
"""
Pydantic schemas for Invoice entities used to validate and structure a bill generated for work performed on a ticket.
"""

from datetime import datetime
from pydantic import BaseModel

class InvoiceBase(BaseModel):
    """Shared fields for Invoice across create/read/update."""
    ticket_id: int
    amount: float
    details: str | None = None
    is_paid: bool

class InvoiceCreate(InvoiceBase):
    """Schema for creating a new Invoice record (client -> server)."""
    pass

class InvoiceUpdate(BaseModel):
    """Schema for partially updating an existing Invoice record. All fields optional."""
    ticket_id: int | None = None
    amount: float | None = None
    details: str | None = None
    is_paid: bool | None = None
    updated_at: datetime | None = None

class Invoice(InvoiceBase):
    """Schema returned to the client for a Invoice record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True
