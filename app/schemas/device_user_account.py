# ER-ServiceDesk/app/schemas/device_user_account.py
# Pydantic schemas for DeviceUserAccount entities
"""
Request/response schemas for a login account known to exist on a
device.

Password is handled as plaintext at this layer in both directions --
the client sends what was typed, and gets back what a tech should see
on the customer's profile. Encryption at rest is purely a
service-layer concern (see device_user_account_service.py); these
schemas never see or need to know about encrypt_password/
decrypt_password.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DeviceUserAccountBase(BaseModel):
    """Shared fields for DeviceUserAccount across create/read/update."""
    device_id: int
    account_name: str
    password: str | None = None
    is_admin: bool = False

class DeviceUserAccountCreate(DeviceUserAccountBase):
    """Schema for creating a new DeviceUserAccount record (client -> server)."""
    pass

class DeviceUserAccountUpdate(BaseModel):
    """Schema for partially updating an existing DeviceUserAccount record. All fields optional."""
    account_name: str | None = None
    password: str | None = None
    is_admin: bool | None = None

class DeviceUserAccount(BaseModel):
    """Schema returned to the client for a DeviceUserAccount record (server -> client). password is decrypted plaintext, not the stored ciphertext."""
    id: int
    device_id: int
    account_name: str
    password: str | None = None
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
