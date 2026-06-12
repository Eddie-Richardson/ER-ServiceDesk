# ER-ServiceDesk/app/services/device_service.py
# Service layer for Device.
#
# Provides business logic for Device operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.device import crud_device
from app.schemas.device import DeviceCreate, DeviceUpdate

class DeviceService:
    # Retrieves a single Device by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Device instance.
        """
        return crud_device.get(db, id)

    # Retrieves multiple Device records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Device records.
        """
        return crud_device.get_multi(db, skip, limit)

    # Creates a new Device.
    def create(self, db: Session, obj_in: DeviceCreate):
        """
        Creates a new Device using validated input data.
        """
        return crud_device.create(db, obj_in)

    # Updates an existing Device.
    def update(self, db: Session, id: int, obj_in: DeviceUpdate):
        """
        Updates an existing Device using validated input data.
        """
        db_obj = crud_device.get(db, id)
        return crud_device.update(db, db_obj, obj_in)

    # Deletes a Device by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Device instance.
        """
        return crud_device.delete(db, id)

device_service = DeviceService()
