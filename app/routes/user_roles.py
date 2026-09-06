# ER-ServiceDesk/app/routes/user_roles.py
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
from app.schemas.user_role import UserRole, UserRoleCreate

router = APIRouter(prefix="/user_roles", tags=["user_roles"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[UserRole])
def list_user_roles(db: Session = Depends(get_db)):
    return user_role_service.get_multi(db)

@router.get("/{id}", response_model=UserRole)
def get_user_role(id: int, db: Session = Depends(get_db)):
    return user_role_service.get(db, id)

@router.post("/", response_model=UserRole)
def create_user_role(
    obj_in: UserRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_role_service.create(db, obj_in, current_user.id)


@router.delete("/{id}")
def delete_user_role(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_role_service.delete(db, id, current_user.id)
