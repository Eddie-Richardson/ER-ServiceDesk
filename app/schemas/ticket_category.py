# ER-ServiceDesk/app/schemas/ticket_category.py
# Pydantic schemas for TicketCategory entities
"""
Request/response schemas for a high-level grouping used to organize
tickets.
"""

from pydantic import BaseModel, ConfigDict

class TicketCategoryBase(BaseModel):
    """Shared fields for TicketCategory across create/read/update."""
    name: str
    description: str | None = None

class TicketCategoryCreate(TicketCategoryBase):
    """Schema for creating a new TicketCategory record (client -> server)."""
    pass

class TicketCategoryUpdate(BaseModel):
    """Schema for partially updating an existing TicketCategory record. All fields optional."""
    name: str | None = None
    description: str | None = None

class TicketCategory(TicketCategoryBase):
    """Schema returned to the client for a TicketCategory record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
