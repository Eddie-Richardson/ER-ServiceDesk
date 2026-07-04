# ER-ServiceDesk/app/routes/parts.py
# API routes for Part operations.
"""
REST endpoints for consumable parts stock, including a low-stock lookup
used to drive the reorder-tracking feature.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.part_service import part_service
from app.crud.part import crud_part
from app.schemas.part import Part, PartCreate, PartUpdate

router = APIRouter(prefix="/inventory/parts", tags=["inventory-parts"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Part])
def list_parts(db: Session = Depends(get_db)):
    """List all parts, paginated."""
    return part_service.get_multi(db)

@router.get("/low-stock", response_model=list[Part])
def list_low_stock_parts(db: Session = Depends(get_db)):
    """
    List every part currently at or below its reorder threshold.

    Args:
        db: Injected database session.

    Returns:
        A list of Part records that need reordering.
    """
    return crud_part.get_low_stock(db)

@router.get("/{id}", response_model=Part)
def get_part(id: int, db: Session = Depends(get_db)):
    """Fetch a single Part record by ID."""
    return part_service.get(db, id)

@router.post("/", response_model=Part)
def create_part(obj_in: PartCreate, db: Session = Depends(get_db)):
    """Create a new Part record. Rejects duplicate SKUs."""
    return part_service.create(db, obj_in)

@router.put("/{id}", response_model=Part)
def update_part(id: int, obj_in: PartUpdate, db: Session = Depends(get_db)):
    """Update an existing Part record."""
    return part_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_part(id: int, db: Session = Depends(get_db)):
    """Delete a Part record by ID."""
    return part_service.delete(db, id)
