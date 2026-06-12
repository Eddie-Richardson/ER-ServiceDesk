# ER-ServiceDesk/app/schemas/devices.py
# Pydantic schemas for Device entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning device records within the ER‑ServiceDesk system.
# They are used for associating devices with customers, linking
# devices to support tickets, and managing hardware information.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class DeviceBase(BaseModel):
    customer_id: int
    device_type: str
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class DeviceCreate(DeviceBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class DeviceUpdate(BaseModel):
    customer_id: int | None = None
    device_type: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Device(DeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True