# ER-ServiceDesk/app/routes/devices.py
# API routes for Device operations.
#
# Exposes REST endpoints for interacting with Device records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.device_service import device_service
from app.schemas.device import Device, DeviceCreate, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("/", response_model=list[Device])
def list_devices(db: Session = Depends(get_db)):
    """
    Returns a list of Device records.
    """
    return device_service.get_multi(db)

@router.get("/{id}", response_model=Device)
def get_device(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Device record by ID.
    """
    return device_service.get(db, id)

@router.post("/", response_model=Device)
def create_device(obj_in: DeviceCreate, db: Session = Depends(get_db)):
    """
    Creates a new Device record.
    """
    return device_service.create(db, obj_in)

@router.put("/{id}", response_model=Device)
def update_device(id: int, obj_in: DeviceUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Device record.
    """
    return device_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_device(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Device record by ID.
    """
    return device_service.delete(db, id)
