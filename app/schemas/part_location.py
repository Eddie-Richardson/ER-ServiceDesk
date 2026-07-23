# ER-ServiceDesk/app/schemas/part_location.py
# Pydantic schemas for PartLocation entities

"""
Request/response schemas for a part's quantity at a specific location.

Always used nested inside Part's own schemas (as the "locations" field)
rather than as a standalone resource -- there's no /part_locations
endpoint, since nothing ever needs to fetch or edit one location-row in
isolation from its owning part.
"""

from pydantic import BaseModel, ConfigDict


class PartLocationInput(BaseModel):
    """
    One location+quantity entry, sent by the client when creating or
    updating a Part's stock breakdown.
    """
    location_id: int
    quantity: int = 0


class PartLocationOut(BaseModel):
    """
    One location+quantity entry as returned to the client. Includes the
    location's name (read via PartLocation.location_name) so the UI can
    display it without a separate lookup.
    """
    location_id: int
    location_name: str | None = None
    quantity: int

    model_config = ConfigDict(from_attributes=True)
