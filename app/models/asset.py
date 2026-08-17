# ER-ServiceDesk/app/models/asset.py
# ORM model for a tracked business asset
"""
ORM model for a serialized, one-off business asset (e.g. a laptop, a bench
tool) -- as opposed to Part, which tracks consumable stock by quantity.
"""

import datetime
from sqlalchemy import Integer, Column, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Asset(Base):
    """
    Represents a single tracked business asset, identified by serial number.

    Attributes:
        status: Current status (e.g. "Active", "In Repair", "Retired").
        price: Purchase price.
        assigned_to: Person or department assigned to the asset -- free
            text, not a User foreign key.
        condition: Physical condition (e.g. "New", "Good", "Damaged").
    """
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    sku = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("asset_categories.id"), nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_number = Column(String, unique=True, nullable=True)

    status = Column(String, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    price = Column(Numeric, nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_expiration = Column(Date, nullable=True)

    assigned_to = Column(String, nullable=True)
    condition = Column(String, nullable=True)
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

    location = relationship("Location", back_populates="assets")
    category = relationship("AssetCategory", back_populates="assets")
