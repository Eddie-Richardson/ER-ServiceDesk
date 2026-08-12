# ER-ServiceDesk/app/services/system_setting_service.py
# Service layer for SystemSetting.
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
        """
        Fetch a single SystemSetting by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching SystemSetting instance, or None if not found.
        """
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

        Args:
            db: Active database session.
            key: The setting's key, e.g. 'lock_timeout_minutes'.
            default: Value to use if the setting is missing or invalid.

        Returns:
            The setting's current value as an int, or default.
        """
        setting = crud_system_setting.get_by_key(db, key)
        if setting is None or setting.value is None:
            return default
        try:
            return int(setting.value)
        except ValueError:
            return default

    def upsert(self, db: Session, key: str, value: str):
        """
        Creates a setting if it doesn't exist yet, or updates it if it
        does -- backs the desktop Settings UI's save action, which
        shouldn't need to know or care whether a given key has ever
        been set before.

        Args:
            db: Active database session.
            key: The setting's key.
            value: The new value to store.

        Returns:
            The created or updated SystemSetting instance.
        """
        setting = crud_system_setting.get_by_key(db, key)
        if setting is None:
            return crud_system_setting.create(db, SystemSettingCreate(key=key, value=value))
        return crud_system_setting.update(db, setting, SystemSettingUpdate(value=value))

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of SystemSetting records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of SystemSetting instances.
        """
        return crud_system_setting.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: SystemSettingCreate):
        """
        Create a new SystemSetting using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created SystemSetting instance.
        """
        return crud_system_setting.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: SystemSettingUpdate):
        """
        Update an existing SystemSetting using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated SystemSetting instance.
        """
        db_obj = crud_system_setting.get(db, id)
        return crud_system_setting.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a SystemSetting by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_system_setting.delete(db, id)

system_setting_service = SystemSettingService()
