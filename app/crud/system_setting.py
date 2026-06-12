# ER-ServiceDesk/app/crud/system_setting.py
# CRUD operations for the SystemSetting model.
#
# Provides database access for creating, reading, updating, and deleting SystemSetting records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.system_setting import SystemSetting
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate

class SystemSettingCRUD:
    # Retrieves a single SystemSetting by ID.
    def get(self, db: Session, id: int) -> SystemSetting | None:
        """
        Returns a single SystemSetting instance matching the given ID.
        """
        return db.query(SystemSetting).filter(SystemSetting.id == id).first()

    # Retrieves multiple SystemSetting records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of SystemSetting records with pagination support.
        """
        return db.query(SystemSetting).offset(skip).limit(limit).all()

    # Creates a new SystemSetting record.
    def create(self, db: Session, obj_in: SystemSettingCreate) -> SystemSetting:
        """
        Creates a new SystemSetting using the provided input schema.
        """
        obj = SystemSetting(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing SystemSetting record.
    def update(self, db: Session, db_obj: SystemSetting, obj_in: SystemSettingUpdate) -> SystemSetting:
        """
        Updates the given SystemSetting instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a SystemSetting record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the SystemSetting instance matching the given ID.
        """
        obj = db.query(SystemSetting).filter(SystemSetting.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_system_setting = SystemSettingCRUD()
