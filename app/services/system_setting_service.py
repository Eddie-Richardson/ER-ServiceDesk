# ER-ServiceDesk/app/services/system_setting_service.py
# Service layer for SystemSetting.
#
# Provides business logic for SystemSetting operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.system_setting import crud_system_setting
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate

class SystemSettingService:
    # Retrieves a single SystemSetting by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single SystemSetting instance.
        """
        return crud_system_setting.get(db, id)

    # Retrieves multiple SystemSetting records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of SystemSetting records.
        """
        return crud_system_setting.get_multi(db, skip, limit)

    # Creates a new SystemSetting.
    def create(self, db: Session, obj_in: SystemSettingCreate):
        """
        Creates a new SystemSetting using validated input data.
        """
        return crud_system_setting.create(db, obj_in)

    # Updates an existing SystemSetting.
    def update(self, db: Session, id: int, obj_in: SystemSettingUpdate):
        """
        Updates an existing SystemSetting using validated input data.
        """
        db_obj = crud_system_setting.get(db, id)
        return crud_system_setting.update(db, db_obj, obj_in)

    # Deletes a SystemSetting by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a SystemSetting instance.
        """
        return crud_system_setting.delete(db, id)

system_setting_service = SystemSettingService()
