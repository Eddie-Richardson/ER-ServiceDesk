# ER-ServiceDesk/app/routes/assets.py
"""
REST endpoints for tracked business assets.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_permission
from app.services.asset_service import asset_service
from app.models.asset import Asset as AssetModel
from app.utils.pagination import paginate_query
from app.schemas.asset import Asset, AssetCreate, AssetUpdate, AssetCreateResponse, PaginationResponse

router = APIRouter(prefix="/inventory/assets", tags=["inventory-assets"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=PaginationResponse)
def list_assets(
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
    page: int | None = None,
    page_size: int | None = None,
):
    """
    Args:
        limit: Items per page (ignored if page/page_size given).
        offset: Items to skip (ignored if page/page_size given).
        page: Page number, 1-indexed -- if given along with page_size,
            overrides limit/offset.
        page_size: Items per page, used with page.
    """
    if page is not None and page_size is not None:
        limit = page_size
        offset = (page - 1) * page_size
    return paginate_query(db.query(AssetModel), limit=limit, offset=offset)

@router.get("/{id}", response_model=Asset)
def get_asset(id: int, db: Session = Depends(get_db)):
    return asset_service.get(db, id)

@router.post("/", response_model=AssetCreateResponse, dependencies=[Depends(require_permission("inventory.manage"))])
def create_asset(obj_in: AssetCreate, db: Session = Depends(get_db)):
    """Rejects duplicate serial numbers."""
    asset = asset_service.create(db, obj_in)
    return {"message": "Asset created successfully", "asset": asset}

@router.put("/{id}", response_model=Asset, dependencies=[Depends(require_permission("inventory.manage"))])
def update_asset(id: int, obj_in: AssetUpdate, db: Session = Depends(get_db)):
    return asset_service.update(db, id, obj_in)

@router.delete("/{id}", dependencies=[Depends(require_permission("inventory.manage"))])
def delete_asset(id: int, db: Session = Depends(get_db)):
    return asset_service.delete(db, id)
