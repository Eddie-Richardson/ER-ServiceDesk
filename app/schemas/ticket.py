# ER-ServiceDesk/app/schemas/ticket.py
# Pydantic schemas for Ticket entities
"""
Pydantic schemas for Ticket entities used to validate and structure a
support/repair job tracked from intake to completion.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TicketBase(BaseModel):
    """Shared fields for Ticket across create/read/update."""
    customer_id: int
    device_id: int
    category_id: int
    type_id: int
    status_id: int
    stage_id: int | None = None
    assigned_to: int | None = None
    current_location_id: int | None = None
    title: str
    description: str | None = None
    priority: str
    pickup_person: str | None = None
    accessories_included: str | None = None

class TicketCreate(TicketBase):
    """Schema for creating a new Ticket record (client -> server)."""
    pass

class TicketUpdate(BaseModel):
    """Schema for partially updating an existing Ticket record. All fields optional."""
    customer_id: int | None = None
    device_id: int | None = None
    category_id: int | None = None
    type_id: int | None = None
    status_id: int | None = None
    stage_id: int | None = None
    assigned_to: int | None = None
    current_location_id: int | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    pickup_person: str | None = None
    accessories_included: str | None = None
    updated_at: datetime | None = None

class Ticket(TicketBase):
    """Schema returned to the client for a Ticket record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
