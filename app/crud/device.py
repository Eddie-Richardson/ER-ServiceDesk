# ER-ServiceDesk/app/crud/device.py
# CRUD operations for the Device model.
#
# Provides database access for creating, reading, updating, and deleting Device records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate

class DeviceCRUD:
    # Retrieves a single Device by ID.
    def get(self, db: Session, id: int) -> Device | None:
        """
        Returns a single Device instance matching the given ID.
        """
        return db.query(Device).filter(Device.id == id).first()

    # Retrieves multiple Device records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Device records with pagination support.
        """
        return db.query(Device).offset(skip).limit(limit).all()

    # Creates a new Device record.
    def create(self, db: Session, obj_in: DeviceCreate) -> Device:
        """
        Creates a new Device using the provided input schema.
        """
        obj = Device(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Device record.
    def update(self, db: Session, db_obj: Device, obj_in: DeviceUpdate) -> Device:
        """
        Updates the given Device instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Device record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Device instance matching the given ID.
        """
        obj = db.query(Device).filter(Device.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_device = DeviceCRUD()
