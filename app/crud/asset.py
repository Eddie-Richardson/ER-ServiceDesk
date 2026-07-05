# ER-ServiceDesk/app/crud/asset.py
# CRUD operations for the Asset model.
"""
Database access layer for tracked business assets. Preserves the
duplicate-serial-number business rule from the original InventoryHub API.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate

class AssetCRUD:
    """Direct database access for Asset records."""

    def get(self, db: Session, id: int) -> Asset | None:
        """
        Fetch a single Asset by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Asset instance, or None if not found.
        """
        return db.query(Asset).filter(Asset.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Asset records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Asset instances.
        """
        return db.query(Asset).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AssetCreate) -> Asset:
        """
        Insert a new Asset record, rejecting duplicate serial numbers.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Asset instance.

        Raises:
            HTTPException: 400 if an asset with the same serial_number
                already exists.
        """
        if obj_in.serial_number:
            existing = db.query(Asset).filter(
                Asset.serial_number == obj_in.serial_number
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Asset with this serial number already exists",
                )

        obj = Asset(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Asset, obj_in: AssetUpdate) -> Asset:
        """
        Apply a partial update to an existing Asset record.

        Args:
            db: Active database session.
            db_obj: The existing Asset instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Asset instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete an Asset record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Asset).filter(Asset.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_asset = AssetCRUD()
