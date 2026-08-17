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
        return crud_asset.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_asset.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AssetCreate):
        return crud_asset.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AssetUpdate):
        db_obj = crud_asset.get(db, id)
        return crud_asset.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_asset.delete(db, id)

asset_service = AssetService()
