# ER-ServiceDesk/app/schemas/part.py
# Pydantic schemas for Part entities
"""
Request/response schemas for consumable, quantity-tracked parts stock.
"""

from datetime import datetime
from pydantic import BaseModel

class PartBase(BaseModel):
    """Shared fields for Part across create/read/update."""
    name: str
    sku: str | None = None
    quantity_on_hand: int = 0
    reorder_threshold: int = 0
    unit_cost: float | None = None
    supplier: str | None = None
    location_id: int | None = None
    notes: str | None = None

class PartCreate(PartBase):
    """Schema for creating a new Part record (client -> server)."""
    pass

class PartUpdate(BaseModel):
    """Schema for partially updating an existing Part record. All fields optional."""
    name: str | None = None
    sku: str | None = None
    quantity_on_hand: int | None = None
    reorder_threshold: int | None = None
    unit_cost: float | None = None
    supplier: str | None = None
    location_id: int | None = None
    notes: str | None = None

class Part(PartBase):
    """Schema returned to the client for a Part record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
