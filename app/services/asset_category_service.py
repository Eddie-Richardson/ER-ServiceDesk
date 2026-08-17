# ER-ServiceDesk/app/services/asset_category_service.py
# Service layer for AssetCategory.

"""
Business logic for a high-level grouping used to organize business assets.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.asset_category import crud_asset_category
from app.schemas.asset_category import AssetCategoryCreate, AssetCategoryUpdate


class AssetCategoryService:
    """Business logic for AssetCategory operations."""

    def get(self, db: Session, id: int):
        return crud_asset_category.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_asset_category.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AssetCategoryCreate):
        return crud_asset_category.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AssetCategoryUpdate):
        db_obj = crud_asset_category.get(db, id)
        return crud_asset_category.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_asset_category.delete(db, id)


asset_category_service = AssetCategoryService()
