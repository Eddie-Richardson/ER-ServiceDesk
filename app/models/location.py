# ER-ServiceDesk/app/models/location.py
"""
ORM model for a physical location, used to anchor asset, part, device,
and ticket "where is it" tracking to a single consistent value instead
of free-text strings that drift out of sync (e.g. "Bench 3" vs "bench3").
"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class Location(Base):
    """
    Represents a single named physical location within the shop (a bench,
    a shelf, a shipping area, etc.).

    Attributes:
        name: Unique location name (e.g. "Bench 3", "Customer Pickup Shelf").
        show_in_ticket_picker: Whether this location appears when
            picking where a customer's device sits during ticket
            creation -- a location like "Parts Shelf" or "Asset
            Inventory" is a genuine location for other purposes (Asset/
            Part tracking) but would never be where a customer's own
            device actually is, so those are seeded False here without
            affecting their availability anywhere else in the app.
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    show_in_ticket_picker = Column(Boolean, nullable=False, default=True)

    assets = relationship("Asset", back_populates="location")
    part_locations = relationship("PartLocation", back_populates="location")
    tickets = relationship("Ticket", back_populates="current_location")
    devices = relationship("Device", back_populates="current_location")
