# ER-ServiceDesk/app/schemas/ticket_status.py
# Pydantic schemas for TicketStatus entities
"""
Request/response schemas for a workflow state a ticket can occupy.
"""

from pydantic import BaseModel, ConfigDict

class TicketStatusBase(BaseModel):
    """Shared fields for TicketStatus across create/read/update."""
    name: str
    description: str | None = None

class TicketStatusCreate(TicketStatusBase):
    """Schema for creating a new TicketStatus record (client -> server)."""
    pass

class TicketStatusUpdate(BaseModel):
    """Schema for partially updating an existing TicketStatus record. All fields optional."""
    name: str | None = None
    description: str | None = None

class TicketStatus(TicketStatusBase):
    """Schema returned to the client for a TicketStatus record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
