# ER-ServiceDesk/app/schemas/discount.py
# Pydantic schemas for Discount entities
"""
Request/response schemas for a named discount category.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class DiscountBase(BaseModel):
    """Shared fields for Discount across create/read/update."""
    name: str
    percentage: Decimal
    is_active: bool = True

class DiscountCreate(DiscountBase):
    """Schema for creating a new Discount record (client -> server)."""
    pass

class DiscountUpdate(BaseModel):
    """Schema for partially updating an existing Discount record. All fields optional."""
    name: str | None = None
    percentage: Decimal | None = None
    is_active: bool | None = None

class Discount(DiscountBase):
    """Schema returned to the client for a Discount record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
