# ER-ServiceDesk/app/models/part.py

"""
ORM model for consumable, quantity-tracked parts stock (e.g. "50x SSD
500GB") -- as opposed to Asset, which tracks serialized one-off items.
This is the model that powers reorder tracking and the auto-notify-
customer-about-parts feature via TicketPart.

A Part is stock-count-agnostic about *where* it physically sits -- that
detail lives in PartLocation, since the same part can be split across
several locations at once (some on the shelf, some at a bench).
quantity_on_hand is a computed total across every PartLocation row
rather than a column on this table, and reorder_threshold is checked
against that total: "we need 5 of these somewhere in the shop," not
"we need 5 at this specific spot."
"""

import datetime
from sqlalchemy import Integer, Column, String, Numeric, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class Part(Base):
    """
    Represents a consumable stock item tracked by quantity, with an
    optional reorder threshold and supplier. Where it physically sits,
    and how much is at each spot, is tracked separately via
    part_locations.

    Attributes:
        reorder_threshold: Total quantity (summed across every location)
            at/below which this part should be reordered.
        selling_price: What this part is billed to a customer at when
            used as a line item on a quote/invoice -- set once here,
            used every time, separate from unit_cost (what the shop
            pays for it) so there's a real, intentional margin rather
            than billing customers at cost. Nullable -- not every part
            in inventory is necessarily meant to be sold to a customer
            (some are shop-internal only); the billing service layer
            requires this to be set before a part can actually be
            added to a line item, rather than requiring it here.
    """
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    sku = Column(String, unique=True, nullable=True)
    reorder_threshold = Column(Integer, nullable=False, default=0)
    unit_cost = Column(Numeric, nullable=True)
    selling_price = Column(Numeric, nullable=True)
    supplier = Column(String, nullable=True)
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

    # cascade="all, delete-orphan": deleting a Part permanently
    # deletes its location/quantity rows with it, not just unlinks them.
    part_locations = relationship(
        "PartLocation", back_populates="part", cascade="all, delete-orphan"
    )
    ticket_parts = relationship("TicketPart", back_populates="part")

    @property
    def quantity_on_hand(self) -> int:
        """
        Returns:
            Total quantity of this part across every location it's
            stored at. Computed rather than stored, so it's always
            consistent with the underlying part_locations rows --
            there's no separate counter that could drift out of sync.
        """
        return sum(pl.quantity for pl in self.part_locations)

    @property
    def locations(self):
        """
        Returns:
            The same rows as part_locations. Exists so the response
            schema's "locations" field (the friendlier external name)
            can be read via Pydantic's from_attributes, which does a
            plain getattr(obj, "locations") -- it has no knowledge of
            the ORM relationship being named part_locations internally.
        """
        return self.part_locations
