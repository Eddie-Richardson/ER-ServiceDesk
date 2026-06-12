# ER-ServiceDesk/app/routes/users.py
# API routes for User operations.
#
# Exposes REST endpoints for interacting with User records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.user_service import user_service
from app.schemas.user import User, UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[User])
def list_users(db: Session = Depends(get_db)):
    """
    Returns a list of User records.
    """
    return user_service.get_multi(db)

@router.get("/{id}", response_model=User)
def get_user(id: int, db: Session = Depends(get_db)):
    """
    Returns a single User record by ID.
    """
    return user_service.get(db, id)

@router.post("/", response_model=User)
def create_user(obj_in: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new User record.
    """
    return user_service.create(db, obj_in)

@router.put("/{id}", response_model=User)
def update_user(id: int, obj_in: UserUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing User record.
    """
    return user_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    """
    Deletes a User record by ID.
    """
    return user_service.delete(db, id)
