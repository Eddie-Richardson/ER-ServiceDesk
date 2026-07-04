# ER-ServiceDesk/app/routes/devices.py
# API routes for Device operations.
"""
REST endpoints for a customer-owned device brought in for service.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.device_service import device_service
from app.schemas.device import Device, DeviceCreate, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Device])
def list_devices(db: Session = Depends(get_db)):
    """
    List a customer-owned device brought in for service, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Device records.
    """
    return device_service.get_multi(db)

@router.get("/{id}", response_model=Device)
def get_device(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Device record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Device record.
    """
    return device_service.get(db, id)

@router.post("/", response_model=Device)
def create_device(obj_in: DeviceCreate, db: Session = Depends(get_db)):
    """
    Create a new Device record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Device record.
    """
    return device_service.create(db, obj_in)

@router.put("/{id}", response_model=Device)
def update_device(id: int, obj_in: DeviceUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Device record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Device record.
    """
    return device_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_device(id: int, db: Session = Depends(get_db)):
    """
    Delete a Device record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return device_service.delete(db, id)
