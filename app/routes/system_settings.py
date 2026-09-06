# ER-ServiceDesk/app/routes/system_settings.py
"""
REST endpoints for a dynamic, admin-editable key/value configuration entry.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.system_setting_service import system_setting_service
from app.schemas.system_setting import SystemSetting, SystemSettingCreate, SystemSettingUpdate

router = APIRouter(prefix="/system_settings", tags=["system_settings"], dependencies=[Depends(require_superuser)])

@router.put("/by-key/{key}", response_model=SystemSetting)
def upsert_system_setting_by_key(key: str, obj_in: SystemSettingUpdate, db: Session = Depends(get_db)):
    """
    Creates or updates a setting by its key name directly -- the
    desktop Settings UI uses this rather than the id-based /{id}
    endpoint below, since it shouldn't need to track a setting's
    numeric id or decide whether the row already exists.
    """
    return system_setting_service.upsert(db, key, obj_in.value)

@router.get("/", response_model=list[SystemSetting])
def list_system_settings(db: Session = Depends(get_db)):
    return system_setting_service.get_multi(db)

@router.get("/{id}", response_model=SystemSetting)
def get_system_setting(id: int, db: Session = Depends(get_db)):
    return system_setting_service.get(db, id)

@router.post("/", response_model=SystemSetting)
def create_system_setting(obj_in: SystemSettingCreate, db: Session = Depends(get_db)):
    return system_setting_service.create(db, obj_in)

@router.put("/{id}", response_model=SystemSetting)
def update_system_setting(id: int, obj_in: SystemSettingUpdate, db: Session = Depends(get_db)):
    return system_setting_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_system_setting(id: int, db: Session = Depends(get_db)):
    return system_setting_service.delete(db, id)
