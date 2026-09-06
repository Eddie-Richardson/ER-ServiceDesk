# ER-ServiceDesk/app/routes/role_permissions.py
"""
REST endpoints for the many-to-many link between roles and permissions.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.role_permission_service import role_permission_service
from app.schemas.role_permission import RolePermission, RolePermissionCreate, RolePermissionUpdate

router = APIRouter(prefix="/role_permissions", tags=["role_permissions"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[RolePermission])
def list_role_permissions(db: Session = Depends(get_db)):
    return role_permission_service.get_multi(db)

@router.get("/{id}", response_model=RolePermission)
def get_role_permission(id: int, db: Session = Depends(get_db)):
    return role_permission_service.get(db, id)

@router.post("/", response_model=RolePermission)
def create_role_permission(obj_in: RolePermissionCreate, db: Session = Depends(get_db)):
    return role_permission_service.create(db, obj_in)

@router.put("/{id}", response_model=RolePermission)
def update_role_permission(id: int, obj_in: RolePermissionUpdate, db: Session = Depends(get_db)):
    return role_permission_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_role_permission(id: int, db: Session = Depends(get_db)):
    return role_permission_service.delete(db, id)
