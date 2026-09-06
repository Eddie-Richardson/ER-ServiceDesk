# ER-ServiceDesk/app/routes/device_user_accounts.py
"""
REST endpoints for a login account known to exist on a device.

Gated the same as routes/devices.py -- any authenticated user, no
specific permission beyond being logged in, matching the parent
resource's own access level.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.device_user_account_service import device_user_account_service
from app.schemas.device_user_account import DeviceUserAccount, DeviceUserAccountCreate, DeviceUserAccountUpdate

router = APIRouter(prefix="/device_user_accounts", tags=["device_user_accounts"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[DeviceUserAccount])
def list_device_user_accounts(device_id: int, db: Session = Depends(get_db)):
    """
    device_id is required (not optional) -- there's no legitimate
    reason to fetch every device's accounts across the whole app at
    once for this endpoint.
    """
    return device_user_account_service.get_by_device(db, device_id)


@router.post("/", response_model=DeviceUserAccount)
def create_device_user_account(
    obj_in: DeviceUserAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return device_user_account_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=DeviceUserAccount)
def update_device_user_account(
    id: int,
    obj_in: DeviceUserAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return device_user_account_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_device_user_account(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return device_user_account_service.delete(db, id, current_user.id)
