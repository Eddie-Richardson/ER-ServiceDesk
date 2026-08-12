# ER-ServiceDesk/app/services/device_service.py
# Service layer for Device.
"""
Business logic for a customer-owned device brought in for service.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.device import crud_device
from app.models.ticket import Ticket
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.services.audit_log_service import audit_log_service

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

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Delete a Device by ID, if it's not currently attached to any
        ticket -- a device with real service history attached needs
        that history dealt with first (reassigned to a different
        device record, or the ticket itself handled), rather than
        silently disappearing out from under it.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user_id: The user performing this deletion --
                recorded in the audit trail.

        Raises:
            HTTPException: 400 if any ticket currently references this
                device.
        """
        attached_ticket = db.query(Ticket).filter(Ticket.device_id == id).first()
        if attached_ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This device is attached to ticket #{attached_ticket.id} and can't be deleted until that's resolved.",
            )

        db_obj = crud_device.get(db, id)
        if db_obj:
            deleted_label = " ".join(filter(None, [db_obj.brand, db_obj.model])) or db_obj.device_type
        else:
            deleted_label = None

        result = crud_device.delete(db, id)

        audit_log_service.log(
            db, "device_deleted", "device", id, user_id=current_user_id,
            details=f"Deleted device: {deleted_label}" if deleted_label else None,
        )

        return result

device_service = DeviceService()
