# ER-ServiceDesk/app/routes/permissions.py
# API routes for Permission operations.
"""
REST endpoints for a single grantable capability in the RBAC system.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.permission_service import permission_service
from app.schemas.permission import Permission, PermissionCreate, PermissionUpdate

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=list[Permission])
def list_permissions(db: Session = Depends(get_db)):
    """
    List a single grantable capability in the RBAC system, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Permission records.
    """
    return permission_service.get_multi(db)

@router.get("/{id}", response_model=Permission)
def get_permission(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Permission record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Permission record.
    """
    return permission_service.get(db, id)

@router.post("/", response_model=Permission)
def create_permission(obj_in: PermissionCreate, db: Session = Depends(get_db)):
    """
    Create a new Permission record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Permission record.
    """
    return permission_service.create(db, obj_in)

@router.put("/{id}", response_model=Permission)
def update_permission(id: int, obj_in: PermissionUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Permission record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Permission record.
    """
    return permission_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_permission(id: int, db: Session = Depends(get_db)):
    """
    Delete a Permission record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return permission_service.delete(db, id)
