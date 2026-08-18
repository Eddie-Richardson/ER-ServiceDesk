# ER-ServiceDesk/app/routes/roles.py
# API routes for Role operations.
"""
REST endpoints for an authorization grouping assigned to users.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.role_service import role_service
from app.schemas.role import Role, RoleCreate, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[Role])
def list_roles(db: Session = Depends(get_db)):
    return role_service.get_multi(db)

@router.get("/{id}", response_model=Role)
def get_role(id: int, db: Session = Depends(get_db)):
    return role_service.get(db, id)

@router.post("/", response_model=Role)
def create_role(obj_in: RoleCreate, db: Session = Depends(get_db)):
    return role_service.create(db, obj_in)

@router.put("/{id}", response_model=Role)
def update_role(id: int, obj_in: RoleUpdate, db: Session = Depends(get_db)):
    return role_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_role(id: int, db: Session = Depends(get_db)):
    return role_service.delete(db, id)
