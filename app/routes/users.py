# ER-ServiceDesk/app/routes/users.py
"""
REST endpoints for staff/system account management.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser, get_current_user
from app.models.user import User as UserModel
from app.services.user_service import user_service
from app.schemas.user import User, UserCreate, UserUpdate, AssignableUser, FirstRunStatus, FirstRunAdminCreate

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_superuser)])

# A second, separate router (not the one above) specifically so this
# one route isn't superuser-gated -- resolving/picking a ticket's
# assignee is something every role genuinely needs, unlike the rest of
# this file's full account-management endpoints. See AssignableUser's
# own docstring for why this is a distinct, narrower schema rather than
# just loosening the main router's gate.
assignable_router = APIRouter(prefix="/users", tags=["users"])

# A third, separate router -- genuinely unauthenticated, no
# dependencies at all. The whole point of the first-run flow is
# reaching it before any account (and therefore any valid login)
# exists yet, so it can't sit behind get_current_user or
# require_superuser the way every other endpoint in this file does.
# create_first_run_admin() itself is what keeps this safe: it
# genuinely re-checks that no account exists at the moment of
# creation, not just trusting whatever the desktop app already
# checked via GET /users/first-run-status.
first_run_router = APIRouter(prefix="/users", tags=["users"])


@first_run_router.get("/first-run-status", response_model=FirstRunStatus)
def get_first_run_status(db: Session = Depends(get_db)):
    """Whether any account exists yet -- the desktop app checks this before showing the Login window."""
    return {"any_exist": user_service.any_exist(db)}


@first_run_router.post("/first-run-admin", response_model=User)
def create_first_run_admin(obj_in: FirstRunAdminCreate, db: Session = Depends(get_db)):
    """Creates the very first account on a fresh install. See UserService.create_first_run_admin() for the real safety check."""
    return user_service.create_first_run_admin(db, obj_in)


@assignable_router.get("/assignable", response_model=list[AssignableUser])
def list_assignable_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Every active user, for resolving a ticket's assigned_to and populating the assignment picker -- available to any authenticated user, not just superusers."""
    return [u for u in user_service.get_multi(db) if u.is_active]

@router.get("/", response_model=list[User])
def list_users(db: Session = Depends(get_db)):
    """Never includes hashed_password."""
    return user_service.get_multi(db)

@router.get("/{id}", response_model=User)
def get_user(id: int, db: Session = Depends(get_db)):
    return user_service.get(db, id)

@router.post("/", response_model=User)
def create_user(
    obj_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Password is hashed server-side."""
    return user_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=User)
def update_user(
    id: int,
    obj_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return user_service.update(db, id, obj_in, current_user.id)

@router.post("/{id}/reset-password", response_model=User)
def reset_user_password(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Generates and emails a new temporary password, forcing the user to set their own on next login. The admin never sees or chooses the new password directly."""
    return user_service.reset_password(db, id, current_user.id)

@router.delete("/{id}")
def delete_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return user_service.delete(db, id, current_user.id)
