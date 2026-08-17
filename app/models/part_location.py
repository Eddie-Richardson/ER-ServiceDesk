# ER-ServiceDesk/app/models/part_location.py
# ORM model for how much of a part is stored at a specific location

"""
ORM model tracking how many units of a Part sit at a specific Location.

A Part can be split across several locations at once (some on the
shelf, some at a bench) -- this table is the "how many, where" detail
underneath a Part, which itself only tracks what the part is (name,
SKU, reorder threshold) not where any of it physically sits. Always
managed as a detail of its owning Part (via Part's create/update, which
replaces the full set of rows for that part in one pass) rather than
exposed as its own standalone CRUD resource.
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class PartLocation(Base):
    """
    Represents the quantity of one Part stored at one Location.
    """
    __tablename__ = "part_locations"
    __table_args__ = (
        UniqueConstraint("part_id", "location_id", name="uq_part_location"),
    )

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)

    part = relationship("Part", back_populates="part_locations")
    location = relationship("Location", back_populates="part_locations")

    @property
    def location_name(self) -> str | None:
        """
        Returns:
            The related Location's name, or None if somehow unset.
            Lets the response schema read this straight off the ORM
            instance via from_attributes, without a separate query.
        """
        return self.location.name if self.location else None
