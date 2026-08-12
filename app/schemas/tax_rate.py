# ER-ServiceDesk/app/schemas/tax_rate.py
# Pydantic schemas for TaxRate entities
"""
Request/response schemas for a named tax rate.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class TaxRateBase(BaseModel):
    """Shared fields for TaxRate across create/read/update."""
    name: str
    percentage: Decimal
    is_active: bool = True

class TaxRateCreate(TaxRateBase):
    """Schema for creating a new TaxRate record (client -> server)."""
    pass

class TaxRateUpdate(BaseModel):
    """Schema for partially updating an existing TaxRate record. All fields optional."""
    name: str | None = None
    percentage: Decimal | None = None
    is_active: bool | None = None

class TaxRate(TaxRateBase):
    """Schema returned to the client for a TaxRate record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
