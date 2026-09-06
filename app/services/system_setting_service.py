# ER-ServiceDesk/app/services/system_setting_service.py
"""
Business logic for a dynamic, admin-editable key/value configuration entry.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.system_setting import crud_system_setting
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate

class SystemSettingService:
    """Business logic for SystemSetting operations."""

    def get(self, db: Session, id: int):
        return crud_system_setting.get(db, id)

    def get_int(self, db: Session, key: str, default: int) -> int:
        """
        Reads a setting's value as an int, with a safe fallback.

        Used by anything reading a tunable value at runtime (e.g.
        record_lock_service's lock timeout, scheduler's poll interval)
        instead of a hardcoded constant. Falls back to default if the
        row doesn't exist yet (a real, expected case -- an install
        upgraded from before this system existed won't have it seeded)
        or if its value somehow isn't a valid integer, rather than
        raising and breaking whatever's trying to read it.
        """
        setting = crud_system_setting.get_by_key(db, key)
        if setting is None or setting.value is None:
            return default
        try:
            return int(setting.value)
        except ValueError:
            return default

    def get_str(self, db: Session, key: str, default: str) -> str:
        """Same reasoning as get_int, for settings that are genuinely text (business name, email address, SMTP/IMAP host, etc.) rather than a tunable number."""
        setting = crud_system_setting.get_by_key(db, key)
        if setting is None or setting.value is None:
            return default
        return setting.value

    def upsert(self, db: Session, key: str, value: str):
        """
        Creates a setting if it doesn't exist yet, or updates it if it
        does -- backs the desktop Settings UI's save action, which
        shouldn't need to know or care whether a given key has ever
        been set before.
        """
        setting = crud_system_setting.get_by_key(db, key)
        if setting is None:
            return crud_system_setting.create(db, SystemSettingCreate(key=key, value=value))
        return crud_system_setting.update(db, setting, SystemSettingUpdate(value=value))

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_system_setting.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: SystemSettingCreate):
        return crud_system_setting.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: SystemSettingUpdate):
        db_obj = crud_system_setting.get(db, id)
        return crud_system_setting.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_system_setting.delete(db, id)

system_setting_service = SystemSettingService()
