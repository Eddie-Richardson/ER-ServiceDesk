# ER-ServiceDesk/app/routes/device_user_accounts.py
"""
REST endpoints for a login account known to exist on a device.

Gated on customers.manage -- looked up while working a ticket for a
device, the same reasoning as messages.py's own gate, but stricter
than plain login given this returns real, decrypted plaintext
credentials rather than just metadata. front_desk incidentally also
gets access this way (no permission exists narrow enough to
distinguish agent from front_desk), which is accepted rather than
building a dedicated permission for a distinction that doesn't
matter in practice yet.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services.device_user_account_service import device_user_account_service
from app.schemas.device_user_account import DeviceUserAccount, DeviceUserAccountCreate, DeviceUserAccountUpdate

router = APIRouter(prefix="/device_user_accounts", tags=["device_user_accounts"], dependencies=[Depends(require_permission("customers.manage"))])


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
