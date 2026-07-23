# ER-ServiceDesk/app/models/asset_category.py
# ORM model for a category used to organize business assets

"""
ORM model for a high-level grouping used to organize tracked business
assets (e.g. "Laptop", "Furniture", "Tool"). Mirrors TicketCategory's
shape -- a small admin-editable lookup table rather than free text, so
asset categories can't drift out of sync ("Laptop" vs "laptop" vs
"Laptops").
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class AssetCategory(Base):
    """
    Represents a broad organizational bucket for business assets.

    Attributes:
        id: Primary key.
        name: Unique category name.
        description: Optional explanation of what falls under this category.
    """
    __tablename__ = "asset_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    assets = relationship("Asset", back_populates="category")
