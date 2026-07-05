# ER-ServiceDesk/app/schemas/quote.py
# Pydantic schemas for Quote entities used to validate and structure an estimated price for ticket-related work, pending customer approval
"""
Pydantic schemas for Quote entities used to validate and structure an estimated price for ticket-related work, pending customer approval.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class QuoteBase(BaseModel):
    """Shared fields for Quote across create/read/update."""
    ticket_id: int
    amount: float
    details: str | None = None

class QuoteCreate(QuoteBase):
    """Schema for creating a new Quote record (client -> server)."""
    pass

class QuoteUpdate(BaseModel):
    """Schema for partially updating an existing Quote record. All fields optional."""
    ticket_id: int | None = None
    amount: float | None = None
    details: str | None = None
    updated_at: datetime | None = None

class Quote(QuoteBase):
    """Schema returned to the client for a Quote record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
