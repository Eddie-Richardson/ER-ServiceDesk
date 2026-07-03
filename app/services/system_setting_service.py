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
