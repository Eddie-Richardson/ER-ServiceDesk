# ER-ServiceDesk/app/schemas/ticket_stage.py
"""
Request/response schemas for the granular repair/build stage a ticket
is at, distinct from its high-level TicketStatus.
"""

from pydantic import BaseModel, ConfigDict

class TicketStageBase(BaseModel):
    """Shared fields for TicketStage across create/read/update."""
    name: str
    description: str | None = None

class TicketStageCreate(TicketStageBase):
    """Schema for creating a new TicketStage record (client -> server)."""
    pass

class TicketStageUpdate(BaseModel):
    """Schema for partially updating an existing TicketStage record. All fields optional."""
    name: str | None = None
    description: str | None = None

class TicketStage(TicketStageBase):
    """Schema returned to the client for a TicketStage record (server -> client)."""
    id: int

    model_config = ConfigDict(from_attributes=True)
