# ER-ServiceDesk/app/schemas/device.py
"""
Request/response schemas for a customer-owned device brought in for
service.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DeviceBase(BaseModel):
    """Shared fields for Device across create/read/update."""
    customer_id: int
    device_type: str
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    os: str | None = None
    edition: str | None = None
    current_location_id: int | None = None

class DeviceCreate(DeviceBase):
    """Schema for creating a new Device record (client -> server)."""
    pass

class DeviceUpdate(BaseModel):
    """Schema for partially updating an existing Device record. All fields optional."""
    customer_id: int | None = None
    device_type: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    os: str | None = None
    edition: str | None = None
    current_location_id: int | None = None
    updated_at: datetime | None = None

class Device(DeviceBase):
    """Schema returned to the client for a Device record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
