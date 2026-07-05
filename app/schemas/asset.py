# ER-ServiceDesk/app/schemas/asset.py
# Pydantic schemas for Asset entities
"""
Request/response schemas for tracked, serialized business assets.
Merged in from the standalone InventoryHub API.
"""

import datetime
from typing import List
from pydantic import BaseModel, ConfigDict

class AssetBase(BaseModel):
    """Shared fields for Asset across create/read/update."""
    name: str
    sku: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    status: str | None = None
    location_id: int | None = None
    price: float | None = None
    purchase_date: datetime.date | None = None
    warranty_expiration: datetime.date | None = None
    assigned_to: str | None = None
    condition: str | None = None
    notes: str | None = None

class AssetCreate(AssetBase):
    """Schema for creating a new Asset record (client -> server)."""
    pass

class AssetUpdate(BaseModel):
    """Schema for partially updating an existing Asset record. All fields optional."""
    name: str | None = None
    sku: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    status: str | None = None
    location_id: int | None = None
    price: float | None = None
    purchase_date: datetime.date | None = None
    warranty_expiration: datetime.date | None = None
    assigned_to: str | None = None
    condition: str | None = None
    notes: str | None = None

class Asset(AssetBase):
    """Schema returned to the client for an Asset record (server -> client)."""
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class AssetCreateResponse(BaseModel):
    """Response wrapper returned when creating a new asset."""
    message: str
    asset: Asset

class PaginationResponse(BaseModel):
    """Generic paginated list response, used by the asset list endpoint."""
    total: int
    limit: int
    offset: int
    count: int
    items: List[dict]
    total_pages: int
    current_page: int
    next_page: bool
    previous_page: bool
