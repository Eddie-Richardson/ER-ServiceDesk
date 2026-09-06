# ER-ServiceDesk/app/crud/system_setting.py
"""
Database access layer for a dynamic, admin-editable key/value configuration entry.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.system_setting import SystemSetting
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate

class SystemSettingCRUD:
    """Direct database access for SystemSetting records."""

    def get(self, db: Session, id: int) -> SystemSetting | None:
        return db.query(SystemSetting).filter(SystemSetting.id == id).first()

    def get_by_key(self, db: Session, key: str) -> SystemSetting | None:
        return db.query(SystemSetting).filter(SystemSetting.key == key).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(SystemSetting).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: SystemSettingCreate) -> SystemSetting:
        obj = SystemSetting(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: SystemSetting, obj_in: SystemSettingUpdate) -> SystemSetting:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(SystemSetting).filter(SystemSetting.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_system_setting = SystemSettingCRUD()
