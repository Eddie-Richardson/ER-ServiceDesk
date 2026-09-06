# ER-ServiceDesk/app/schemas/ticket_type_stage.py
"""
Request/response schemas for the (ticket type, stage) allow-list used to
restrict which TicketStage values are valid for a given TicketType.
"""

from pydantic import BaseModel, ConfigDict

class TicketTypeStageBase(BaseModel):
    """Shared fields for TicketTypeStage across create/read/update."""
    type_id: int
    stage_id: int

class TicketTypeStageCreate(TicketTypeStageBase):
    """Schema for creating a new TicketTypeStage record (client -> server)."""
    pass

class TicketTypeStageUpdate(BaseModel):
    """Schema for partially updating an existing TicketTypeStage record. All fields optional."""
    type_id: int | None = None
    stage_id: int | None = None

class TicketTypeStage(TicketTypeStageBase):
    """Schema returned to the client for a TicketTypeStage record (server -> client)."""
    id: int

    model_config = ConfigDict(from_attributes=True)
