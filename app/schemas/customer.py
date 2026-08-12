# ER-ServiceDesk/app/schemas/customer.py
# Pydantic schemas for Customer entities used to validate and structure a client of the repair shop
"""
Pydantic schemas for Customer entities used to validate and structure a client of the repair shop.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CustomerBase(BaseModel):
    """Shared fields for Customer across create/read/update."""
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    address: str | None = None

class CustomerCreate(CustomerBase):
    """Schema for creating a new Customer record (client -> server)."""
    pass

class CustomerUpdate(BaseModel):
    """Schema for partially updating an existing Customer record. All fields optional."""
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    is_archived: bool | None = None
    updated_at: datetime | None = None

class Customer(CustomerBase):
    """Schema returned to the client for a Customer record (server -> client)."""
    id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
