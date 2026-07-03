# ER-ServiceDesk/app/schemas/message.py
# Pydantic schemas for Message entities used to validate and structure a customer-facing message exchanged on a ticket (e.g. via email)
"""
Pydantic schemas for Message entities used to validate and structure a customer-facing message exchanged on a ticket (e.g. via email).
"""

from datetime import datetime
from pydantic import BaseModel

class MessageBase(BaseModel):
    """Shared fields for Message across create/read/update."""
    ticket_id: int
    customer_id: int
    direction: str
    content: str

class MessageCreate(MessageBase):
    """Schema for creating a new Message record (client -> server)."""
    pass

class MessageUpdate(BaseModel):
    """Schema for partially updating an existing Message record. All fields optional."""
    ticket_id: int | None = None
    customer_id: int | None = None
    direction: str | None = None
    content: str | None = None
    updated_at: datetime | None = None

class Message(MessageBase):
    """Schema returned to the client for a Message record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True
