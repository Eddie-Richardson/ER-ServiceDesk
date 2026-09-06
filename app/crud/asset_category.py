# ER-ServiceDesk/app/crud/asset_category.py

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
        return db.query(AssetCategory).filter(AssetCategory.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(AssetCategory).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AssetCategoryCreate) -> AssetCategory:
        obj = AssetCategory(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: AssetCategory, obj_in: AssetCategoryUpdate) -> AssetCategory:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(AssetCategory).filter(AssetCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


crud_asset_category = AssetCategoryCRUD()
