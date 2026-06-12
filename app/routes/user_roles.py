# ER-ServiceDesk/app/routes/user_roles.py
# API routes for UserRole operations.
#
# Exposes REST endpoints for interacting with UserRole records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.user_role_service import user_role_service
from app.schemas.user_role import UserRole, UserRoleCreate, UserRoleUpdate

router = APIRouter(prefix="/user_roles", tags=["user_roles"])

@router.get("/", response_model=list[UserRole])
def list_user_roles(db: Session = Depends(get_db)):
    """
    Returns a list of UserRole records.
    """
    return user_role_service.get_multi(db)

@router.get("/{id}", response_model=UserRole)
def get_user_role(id: int, db: Session = Depends(get_db)):
    """
    Returns a single UserRole record by ID.
    """
    return user_role_service.get(db, id)

@router.post("/", response_model=UserRole)
def create_user_role(obj_in: UserRoleCreate, db: Session = Depends(get_db)):
    """
    Creates a new UserRole record.
    """
    return user_role_service.create(db, obj_in)

@router.put("/{id}", response_model=UserRole)
def update_user_role(id: int, obj_in: UserRoleUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing UserRole record.
    """
    return user_role_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_user_role(id: int, db: Session = Depends(get_db)):
    """
    Deletes a UserRole record by ID.
    """
    return user_role_service.delete(db, id)
