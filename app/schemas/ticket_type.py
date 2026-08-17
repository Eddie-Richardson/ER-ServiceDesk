# ER-ServiceDesk/app/schemas/ticket_type.py
# Pydantic schemas for TicketType entities
"""
Request/response schemas for a classification of the kind of work a
ticket represents.
"""

from pydantic import BaseModel, ConfigDict

class TicketTypeBase(BaseModel):
    """Shared fields for TicketType across create/read/update."""
    name: str
    description: str | None = None

class TicketTypeCreate(TicketTypeBase):
    """Schema for creating a new TicketType record (client -> server)."""
    pass

class TicketTypeUpdate(BaseModel):
    """Schema for partially updating an existing TicketType record. All fields optional."""
    name: str | None = None
    description: str | None = None

class TicketType(TicketTypeBase):
    """Schema returned to the client for a TicketType record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
