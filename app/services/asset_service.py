# ER-ServiceDesk/app/services/asset_service.py
# Service layer for Asset.
"""
Business logic for Asset operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

from sqlalchemy.orm import Session
from app.crud.asset import crud_asset
from app.schemas.asset import AssetCreate, AssetUpdate

class AssetService:
    """Business logic for Asset operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Asset by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Asset instance, or None if not found.
        """
        return crud_asset.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Asset records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Asset instances.
        """
        return crud_asset.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AssetCreate):
        """
        Create a new Asset using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Asset instance.
        """
        return crud_asset.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AssetUpdate):
        """
        Update an existing Asset using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Asset instance.
        """
        db_obj = crud_asset.get(db, id)
        return crud_asset.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Asset by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_asset.delete(db, id)

asset_service = AssetService()
