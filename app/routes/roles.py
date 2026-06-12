# ER-ServiceDesk/app/routes/roles.py
# API routes for Role operations.
#
# Exposes REST endpoints for interacting with Role records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.role_service import role_service
from app.schemas.role import Role, RoleCreate, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("/", response_model=list[Role])
def list_roles(db: Session = Depends(get_db)):
    """
    Returns a list of Role records.
    """
    return role_service.get_multi(db)

@router.get("/{id}", response_model=Role)
def get_role(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Role record by ID.
    """
    return role_service.get(db, id)

@router.post("/", response_model=Role)
def create_role(obj_in: RoleCreate, db: Session = Depends(get_db)):
    """
    Creates a new Role record.
    """
    return role_service.create(db, obj_in)

@router.put("/{id}", response_model=Role)
def update_role(id: int, obj_in: RoleUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Role record.
    """
    return role_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_role(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Role record by ID.
    """
    return role_service.delete(db, id)
