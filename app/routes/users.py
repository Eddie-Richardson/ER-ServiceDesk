# ER-ServiceDesk/app/routes/users.py
# API routes for User operations.
"""
REST endpoints for staff/system account management.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.user_service import user_service
from app.schemas.user import User, UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[User])
def list_users(db: Session = Depends(get_db)):
    """
    List user accounts, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of User records (never includes hashed_password).
    """
    return user_service.get_multi(db)

@router.get("/{id}", response_model=User)
def get_user(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single user account by ID.

    Args:
        id: Primary key of the user to fetch.
        db: Injected database session.

    Returns:
        The matching User record.
    """
    return user_service.get(db, id)

@router.post("/", response_model=User)
def create_user(obj_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account. Password is hashed server-side.

    Args:
        obj_in: New account details, including a plaintext password.
        db: Injected database session.

    Returns:
        The newly created User record.
    """
    return user_service.create(db, obj_in)

@router.put("/{id}", response_model=User)
def update_user(id: int, obj_in: UserUpdate, db: Session = Depends(get_db)):
    """
    Update an existing user account.

    Args:
        id: Primary key of the user to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated User record.
    """
    return user_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    """
    Delete a user account by ID.

    Args:
        id: Primary key of the user to delete.
        db: Injected database session.
    """
    return user_service.delete(db, id)
