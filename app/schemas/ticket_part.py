# ER-ServiceDesk/app/schemas/ticket_part.py
# Pydantic schemas for TicketPart entities
"""
Request/response schemas for a part requirement on a ticket, and its
fulfillment status (needed/ordered/backordered/received/installed).
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TicketPartBase(BaseModel):
    """Shared fields for TicketPart across create/read/update."""
    ticket_id: int
    part_id: int
    quantity_needed: int = 1
    status: str = "needed"
    notes: str | None = None

class TicketPartCreate(TicketPartBase):
    """Schema for creating a new TicketPart record (client -> server)."""
    pass

class TicketPartUpdate(BaseModel):
    """Schema for partially updating an existing TicketPart record. All fields optional."""
    quantity_needed: int | None = None
    status: str | None = None
    ordered_at: datetime | None = None
    received_at: datetime | None = None
    notes: str | None = None

class TicketPart(TicketPartBase):
    """Schema returned to the client for a TicketPart record (server -> client)."""
    id: int
    ordered_at: datetime | None = None
    received_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
