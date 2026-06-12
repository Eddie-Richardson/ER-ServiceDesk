# ER-ServiceDesk/app/routes/permissions.py
# API routes for Permission operations.
#
# Exposes REST endpoints for interacting with Permission records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.permission_service import permission_service
from app.schemas.permission import Permission, PermissionCreate, PermissionUpdate

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=list[Permission])
def list_permissions(db: Session = Depends(get_db)):
    """
    Returns a list of Permission records.
    """
    return permission_service.get_multi(db)

@router.get("/{id}", response_model=Permission)
def get_permission(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Permission record by ID.
    """
    return permission_service.get(db, id)

@router.post("/", response_model=Permission)
def create_permission(obj_in: PermissionCreate, db: Session = Depends(get_db)):
    """
    Creates a new Permission record.
    """
    return permission_service.create(db, obj_in)

@router.put("/{id}", response_model=Permission)
def update_permission(id: int, obj_in: PermissionUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Permission record.
    """
    return permission_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_permission(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Permission record by ID.
    """
    return permission_service.delete(db, id)
