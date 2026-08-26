# ER-ServiceDesk/app/schemas/location.py
# Pydantic schemas for Location entities
"""
Request/response schemas for named physical locations (benches, shelves,
shipping areas) used to anchor asset, part, and ticket location tracking.
"""

from pydantic import BaseModel, ConfigDict

class LocationBase(BaseModel):
    """Shared fields for Location across create/read/update."""
    name: str
    description: str | None = None
    show_in_ticket_picker: bool = True

class LocationCreate(LocationBase):
    """Schema for creating a new Location record (client -> server)."""
    pass

class LocationUpdate(BaseModel):
    """Schema for partially updating an existing Location record. All fields optional."""
    name: str | None = None
    description: str | None = None
    show_in_ticket_picker: bool | None = None

class Location(LocationBase):
    """Schema returned to the client for a Location record (server -> client)."""
    id: int

    model_config = ConfigDict(from_attributes=True)
