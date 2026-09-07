# ER-ServiceDesk/app/services/asset_service.py
"""
Business logic for Asset operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

from sqlalchemy.orm import Session
from app.crud.asset import crud_asset
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.audit_log_service import audit_log_service

class AssetService:
    """Business logic for Asset operations."""

    def get(self, db: Session, id: int):
        return crud_asset.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_asset.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AssetCreate, current_user_id: int):
        new_asset = crud_asset.create(db, obj_in)
        audit_log_service.log(
            db, "asset_created", "asset", new_asset.id, user_id=current_user_id,
            details=f"Created asset: {new_asset.name} (serial: {new_asset.serial_number})",
        )
        return new_asset

    def update(self, db: Session, id: int, obj_in: AssetUpdate, current_user_id: int):
        db_obj = crud_asset.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)
        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_asset.update(db, db_obj, obj_in)

        if changed_fields:
            audit_log_service.log(
                db, "asset_updated", "asset", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

    def delete(self, db: Session, id: int):
        return crud_asset.delete(db, id)

asset_service = AssetService()
