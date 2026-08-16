# ER-ServiceDesk/app/schemas/part.py
# Pydantic schemas for Part entities

"""
Request/response schemas for consumable, quantity-tracked parts stock.

quantity_on_hand and locations are read-only on the response side --
computed from the underlying part_locations rows (see the Part model's
quantity_on_hand property). To change where/how much of a part is
stored, send a "locations" list on create/update; the service layer
replaces the full set of location rows for that part with whatever list
is given (see PartService._replace_locations), rather than trying to
diff individual entries.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.schemas.part_location import PartLocationInput, PartLocationOut


class PartBase(BaseModel):
    """Shared fields for Part across create/read/update."""
    name: str
    sku: str | None = None
    reorder_threshold: int = 0
    unit_cost: float | None = None
    selling_price: Decimal | None = None
    supplier: str | None = None
    notes: str | None = None


class PartCreate(PartBase):
    """
    Schema for creating a new Part record (client -> server).

    locations: The initial stock breakdown, e.g.
        [{"location_id": 1, "quantity": 2}, {"location_id": 3, "quantity": 1}].
        Omit or send an empty list to create the part with no stock yet.
    """
    locations: list[PartLocationInput] = []


class PartUpdate(BaseModel):
    """
    Schema for partially updating an existing Part record. All fields
    optional.

    locations: If given, replaces the part's entire stock breakdown with
        this list. If omitted (None), the existing breakdown is left
        untouched -- so an update that only changes, say, supplier
        doesn't require resending the full location list.
    """
    name: str | None = None
    sku: str | None = None
    reorder_threshold: int | None = None
    unit_cost: float | None = None
    selling_price: Decimal | None = None
    supplier: str | None = None
    notes: str | None = None
    locations: list[PartLocationInput] | None = None


class Part(PartBase):
    """Schema returned to the client for a Part record (server -> client)."""
    id: int
    quantity_on_hand: int
    locations: list[PartLocationOut]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
