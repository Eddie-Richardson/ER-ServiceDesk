# ER-ServiceDesk/app/schemas/asset_category.py
# Pydantic schemas for AssetCategory entities

"""
Request/response schemas for a high-level grouping used to organize
business assets.
"""

from pydantic import BaseModel, ConfigDict


class AssetCategoryBase(BaseModel):
    """Shared fields for AssetCategory across create/read/update."""
    name: str
    description: str | None = None


class AssetCategoryCreate(AssetCategoryBase):
    """Schema for creating a new AssetCategory record (client -> server)."""
    pass


class AssetCategoryUpdate(BaseModel):
    """Schema for partially updating an existing AssetCategory record. All fields optional."""
    name: str | None = None
    description: str | None = None


class AssetCategory(AssetCategoryBase):
    """Schema returned to the client for an AssetCategory record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
