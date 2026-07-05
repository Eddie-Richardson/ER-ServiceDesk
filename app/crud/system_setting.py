# ER-ServiceDesk/app/crud/system_setting.py
# CRUD operations for the SystemSetting model.
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
        """
        Fetch a single SystemSetting by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching SystemSetting instance, or None if no record exists.
        """
        return db.query(SystemSetting).filter(SystemSetting.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple SystemSetting records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of SystemSetting instances.
        """
        return db.query(SystemSetting).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: SystemSettingCreate) -> SystemSetting:
        """
        Insert a new SystemSetting record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed SystemSetting instance.
        """
        obj = SystemSetting(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: SystemSetting, obj_in: SystemSettingUpdate) -> SystemSetting:
        """
        Apply a partial update to an existing SystemSetting record.

        Args:
            db: Active database session.
            db_obj: The existing SystemSetting instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed SystemSetting instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a SystemSetting record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(SystemSetting).filter(SystemSetting.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_system_setting = SystemSettingCRUD()
