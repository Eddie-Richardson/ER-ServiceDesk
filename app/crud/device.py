# ER-ServiceDesk/app/crud/device.py
# CRUD operations for the Device model.
"""
Database access layer for a customer-owned device brought in for service.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate

class DeviceCRUD:
    """Direct database access for Device records."""

    def get(self, db: Session, id: int) -> Device | None:
        """
        Fetch a single Device by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Device instance, or None if no record exists.
        """
        return db.query(Device).filter(Device.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Device records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Device instances.
        """
        return db.query(Device).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: DeviceCreate) -> Device:
        """
        Insert a new Device record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Device instance.
        """
        obj = Device(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Device, obj_in: DeviceUpdate) -> Device:
        """
        Apply a partial update to an existing Device record.

        Args:
            db: Active database session.
            db_obj: The existing Device instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Device instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Device record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Device).filter(Device.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_device = DeviceCRUD()
