# ER-ServiceDesk/app/routes/parts.py
# API routes for Part operations.
"""
REST endpoints for consumable parts stock.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_permission
from app.services.part_service import part_service
from app.schemas.part import Part, PartCreate, PartUpdate

router = APIRouter(prefix="/inventory/parts", tags=["inventory-parts"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Part])
def list_parts(db: Session = Depends(get_db)):
    return part_service.get_multi(db)

@router.get("/{id}", response_model=Part)
def get_part(id: int, db: Session = Depends(get_db)):
    return part_service.get(db, id)

@router.post("/", response_model=Part, dependencies=[Depends(require_permission("inventory.manage"))])
def create_part(obj_in: PartCreate, db: Session = Depends(get_db)):
    """Rejects duplicate SKUs."""
    return part_service.create(db, obj_in)

@router.put("/{id}", response_model=Part, dependencies=[Depends(require_permission("inventory.manage"))])
def update_part(id: int, obj_in: PartUpdate, db: Session = Depends(get_db)):
    return part_service.update(db, id, obj_in)

@router.delete("/{id}", dependencies=[Depends(require_permission("inventory.manage"))])
def delete_part(id: int, db: Session = Depends(get_db)):
    return part_service.delete(db, id)
