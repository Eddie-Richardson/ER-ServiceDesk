# ER-ServiceDesk/app/routes/system_settings.py
# API routes for SystemSetting operations.
"""
REST endpoints for a dynamic, admin-editable key/value configuration entry.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.system_setting_service import system_setting_service
from app.schemas.system_setting import SystemSetting, SystemSettingCreate, SystemSettingUpdate

router = APIRouter(prefix="/system_settings", tags=["system_settings"])

@router.get("/", response_model=list[SystemSetting])
def list_system_settings(db: Session = Depends(get_db)):
    """
    List a dynamic, admin-editable key/value configuration entry, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of SystemSetting records.
    """
    return system_setting_service.get_multi(db)

@router.get("/{id}", response_model=SystemSetting)
def get_system_setting(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single SystemSetting record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching SystemSetting record.
    """
    return system_setting_service.get(db, id)

@router.post("/", response_model=SystemSetting)
def create_system_setting(obj_in: SystemSettingCreate, db: Session = Depends(get_db)):
    """
    Create a new SystemSetting record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created SystemSetting record.
    """
    return system_setting_service.create(db, obj_in)

@router.put("/{id}", response_model=SystemSetting)
def update_system_setting(id: int, obj_in: SystemSettingUpdate, db: Session = Depends(get_db)):
    """
    Update an existing SystemSetting record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated SystemSetting record.
    """
    return system_setting_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_system_setting(id: int, db: Session = Depends(get_db)):
    """
    Delete a SystemSetting record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return system_setting_service.delete(db, id)
