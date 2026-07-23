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
        """
        Fetch a single AssetCategory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching AssetCategory instance, or None if not found.
        """
        return crud_asset_category.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of AssetCategory records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of AssetCategory instances.
        """
        return crud_asset_category.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AssetCategoryCreate):
        """
        Create a new AssetCategory using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created AssetCategory instance.
        """
        return crud_asset_category.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AssetCategoryUpdate):
        """
        Update an existing AssetCategory using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated AssetCategory instance.
        """
        db_obj = crud_asset_category.get(db, id)
        return crud_asset_category.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete an AssetCategory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_asset_category.delete(db, id)


asset_category_service = AssetCategoryService()
