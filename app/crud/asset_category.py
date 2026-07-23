# ER-ServiceDesk/app/crud/asset_category.py
# CRUD operations for the AssetCategory model.

"""
Database access layer for a high-level grouping used to organize
business assets.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.asset_category import AssetCategory
from app.schemas.asset_category import AssetCategoryCreate, AssetCategoryUpdate


class AssetCategoryCRUD:
    """Direct database access for AssetCategory records."""

    def get(self, db: Session, id: int) -> AssetCategory | None:
        """
        Fetch a single AssetCategory by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching AssetCategory instance, or None if no record exists.
        """
        return db.query(AssetCategory).filter(AssetCategory.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple AssetCategory records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of AssetCategory instances.
        """
        return db.query(AssetCategory).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AssetCategoryCreate) -> AssetCategory:
        """
        Insert a new AssetCategory record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed AssetCategory instance.
        """
        obj = AssetCategory(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: AssetCategory, obj_in: AssetCategoryUpdate) -> AssetCategory:
        """
        Apply a partial update to an existing AssetCategory record.

        Args:
            db: Active database session.
            db_obj: The existing AssetCategory instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed AssetCategory instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete an AssetCategory record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(AssetCategory).filter(AssetCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


crud_asset_category = AssetCategoryCRUD()
