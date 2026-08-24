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
from app.models.user import User
from app.services.device_service import device_service
from app.schemas.device import Device, DeviceCreate, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Device])
def list_devices(db: Session = Depends(get_db)):
    return device_service.get_multi(db)

@router.get("/{id}", response_model=Device)
def get_device(id: int, db: Session = Depends(get_db)):
    return device_service.get(db, id)

@router.post("/", response_model=Device)
def create_device(obj_in: DeviceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return device_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=Device)
def update_device(id: int, obj_in: DeviceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return device_service.update(db, id, obj_in, current_user.id)

@router.delete("/{id}")
def delete_device(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return device_service.delete(db, id, current_user.id)
