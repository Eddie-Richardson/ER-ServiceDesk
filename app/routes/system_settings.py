# ER-ServiceDesk/app/routes/system_settings.py
# API routes for SystemSetting operations.
#
# Exposes REST endpoints for interacting with SystemSetting records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.system_setting_service import system_setting_service
from app.schemas.system_setting import SystemSetting, SystemSettingCreate, SystemSettingUpdate

router = APIRouter(prefix="/system_settings", tags=["system_settings"])

@router.get("/", response_model=list[SystemSetting])
def list_system_settings(db: Session = Depends(get_db)):
    """
    Returns a list of SystemSetting records.
    """
    return system_setting_service.get_multi(db)

@router.get("/{id}", response_model=SystemSetting)
def get_system_setting(id: int, db: Session = Depends(get_db)):
    """
    Returns a single SystemSetting record by ID.
    """
    return system_setting_service.get(db, id)

@router.post("/", response_model=SystemSetting)
def create_system_setting(obj_in: SystemSettingCreate, db: Session = Depends(get_db)):
    """
    Creates a new SystemSetting record.
    """
    return system_setting_service.create(db, obj_in)

@router.put("/{id}", response_model=SystemSetting)
def update_system_setting(id: int, obj_in: SystemSettingUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing SystemSetting record.
    """
    return system_setting_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_system_setting(id: int, db: Session = Depends(get_db)):
    """
    Deletes a SystemSetting record by ID.
    """
    return system_setting_service.delete(db, id)
