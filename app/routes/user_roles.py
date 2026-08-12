# ER-ServiceDesk/app/routes/user_roles.py
# API routes for UserRole operations.
"""
REST endpoints for the many-to-many link between users and roles.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser, get_current_user
from app.models.user import User
from app.services.user_role_service import user_role_service
from app.schemas.user_role import UserRole, UserRoleCreate, UserRoleUpdate

router = APIRouter(prefix="/user_roles", tags=["user_roles"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[UserRole])
def list_user_roles(db: Session = Depends(get_db)):
    """
    List the many-to-many link between users and roles, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of UserRole records.
    """
    return user_role_service.get_multi(db)

@router.get("/{id}", response_model=UserRole)
def get_user_role(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single UserRole record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching UserRole record.
    """
    return user_role_service.get(db, id)

@router.post("/", response_model=UserRole)
def create_user_role(
    obj_in: UserRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Grant a role to a user.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.
        current_user: The admin granting this role -- recorded in the
            audit trail.

    Returns:
        The newly created UserRole record.
    """
    return user_role_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=UserRole)
def update_user_role(id: int, obj_in: UserRoleUpdate, db: Session = Depends(get_db)):
    """
    Update an existing UserRole record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated UserRole record.
    """
    return user_role_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_user_role(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a role from a user.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
        current_user: The admin revoking this role -- recorded in the
            audit trail.
    """
    return user_role_service.delete(db, id, current_user.id)
