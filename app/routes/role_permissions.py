# ER-ServiceDesk/app/routes/role_permissions.py
# API routes for RolePermission operations.
#
# Exposes REST endpoints for interacting with RolePermission records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.role_permission_service import role_permission_service
from app.schemas.role_permission import RolePermission, RolePermissionCreate, RolePermissionUpdate

router = APIRouter(prefix="/role_permissions", tags=["role_permissions"])

@router.get("/", response_model=list[RolePermission])
def list_role_permissions(db: Session = Depends(get_db)):
    """
    Returns a list of RolePermission records.
    """
    return role_permission_service.get_multi(db)

@router.get("/{id}", response_model=RolePermission)
def get_role_permission(id: int, db: Session = Depends(get_db)):
    """
    Returns a single RolePermission record by ID.
    """
    return role_permission_service.get(db, id)

@router.post("/", response_model=RolePermission)
def create_role_permission(obj_in: RolePermissionCreate, db: Session = Depends(get_db)):
    """
    Creates a new RolePermission record.
    """
    return role_permission_service.create(db, obj_in)

@router.put("/{id}", response_model=RolePermission)
def update_role_permission(id: int, obj_in: RolePermissionUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing RolePermission record.
    """
    return role_permission_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_role_permission(id: int, db: Session = Depends(get_db)):
    """
    Deletes a RolePermission record by ID.
    """
    return role_permission_service.delete(db, id)
