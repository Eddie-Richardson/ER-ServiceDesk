# ER-ServiceDesk/app/schemas/service.py
# Pydantic schemas for Service entities
"""
Request/response schemas for a billable service the shop offers.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class ServiceBase(BaseModel):
    """Shared fields for Service across create/read/update."""
    name: str
    description: str | None = None
    price: Decimal
    is_active: bool = True

class ServiceCreate(ServiceBase):
    """Schema for creating a new Service record (client -> server)."""
    pass

class ServiceUpdate(BaseModel):
    """Schema for partially updating an existing Service record. All fields optional."""
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    is_active: bool | None = None

class Service(ServiceBase):
    """Schema returned to the client for a Service record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
