# ER-ServiceDesk/app/routes/assets.py
# API routes for Asset operations.
"""
REST endpoints for tracked business assets. Preserves the paginated-list
and wrapped-create-response shape from the original InventoryHub API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
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
    List assets with offset- or page-based pagination.

    Args:
        db: Injected database session.
        limit: Items per page (ignored if page/page_size given).
        offset: Items to skip (ignored if page/page_size given).
        page: Page number, 1-indexed.
        page_size: Items per page.

    Returns:
        A paginated response with items + page metadata.
    """
    if page is not None and page_size is not None:
        limit = page_size
        offset = (page - 1) * page_size
    return paginate_query(db.query(AssetModel), limit=limit, offset=offset)

@router.get("/{id}", response_model=Asset)
def get_asset(id: int, db: Session = Depends(get_db)):
    """Fetch a single Asset record by ID."""
    return asset_service.get(db, id)

@router.post("/", response_model=AssetCreateResponse)
def create_asset(obj_in: AssetCreate, db: Session = Depends(get_db)):
    """
    Create a new asset. Rejects duplicate serial numbers.

    Returns:
        A message plus the newly created Asset record.
    """
    asset = asset_service.create(db, obj_in)
    return {"message": "Asset created successfully", "asset": asset}

@router.put("/{id}", response_model=Asset)
def update_asset(id: int, obj_in: AssetUpdate, db: Session = Depends(get_db)):
    """Update an existing Asset record."""
    return asset_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_asset(id: int, db: Session = Depends(get_db)):
    """Delete an Asset record by ID."""
    return asset_service.delete(db, id)
