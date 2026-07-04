# ER-ServiceDesk/app/models/part.py
# ORM model for consumable parts stock
"""
ORM model for consumable, quantity-tracked parts stock (e.g. "50x SSD
500GB") -- as opposed to Asset, which tracks serialized one-off items.
This is the model that powers reorder tracking and the auto-notify-
customer-about-parts feature via TicketPart.
"""

import datetime
from sqlalchemy import Integer, Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Part(Base):
    """
    Represents a consumable stock item tracked by quantity, with an
    optional reorder threshold and supplier.

    Attributes:
        id: Primary key.
        name: Part name (e.g. "SSD 500GB").
        sku: Unique stock-keeping unit identifier.
        quantity_on_hand: Current quantity in stock.
        reorder_threshold: Quantity at/below which this part should be
            reordered.
        unit_cost: Cost per unit.
        supplier: Optional preferred supplier name.
        location_id: The Location this part is stored at.
        notes: Optional free-text notes.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    sku = Column(String, unique=True, nullable=True)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=0)
    unit_cost = Column(Numeric, nullable=True)
    supplier = Column(String, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    notes = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    location = relationship("Location", back_populates="parts")
    ticket_parts = relationship("TicketPart", back_populates="part")
