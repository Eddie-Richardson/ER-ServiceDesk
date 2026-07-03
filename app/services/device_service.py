# ER-ServiceDesk/app/services/device_service.py
# Service layer for Device.
"""
Business logic for a customer-owned device brought in for service.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.device import crud_device
from app.schemas.device import DeviceCreate, DeviceUpdate

class DeviceService:
    """Business logic for Device operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Device by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Device instance, or None if not found.
        """
        return crud_device.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Device records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Device instances.
        """
        return crud_device.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: DeviceCreate):
        """
        Create a new Device using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Device instance.
        """
        return crud_device.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: DeviceUpdate):
        """
        Update an existing Device using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Device instance.
        """
        db_obj = crud_device.get(db, id)
        return crud_device.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Device by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_device.delete(db, id)

device_service = DeviceService()
