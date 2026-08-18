# ER-ServiceDesk/app/routes/asset_categories.py
# API routes for AssetCategory operations.

"""
REST endpoints for a high-level grouping used to organize business assets.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.asset_category_service import asset_category_service
from app.schemas.asset_category import AssetCategory, AssetCategoryCreate, AssetCategoryUpdate

router = APIRouter(prefix="/inventory/asset_categories", tags=["inventory-asset-categories"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[AssetCategory])
def list_asset_categories(db: Session = Depends(get_db)):
    return asset_category_service.get_multi(db)


@router.get("/{id}", response_model=AssetCategory)
def get_asset_category(id: int, db: Session = Depends(get_db)):
    return asset_category_service.get(db, id)


@router.post("/", response_model=AssetCategory)
def create_asset_category(obj_in: AssetCategoryCreate, db: Session = Depends(get_db)):
    return asset_category_service.create(db, obj_in)


@router.put("/{id}", response_model=AssetCategory)
def update_asset_category(id: int, obj_in: AssetCategoryUpdate, db: Session = Depends(get_db)):
    return asset_category_service.update(db, id, obj_in)


@router.delete("/{id}")
def delete_asset_category(id: int, db: Session = Depends(get_db)):
    return asset_category_service.delete(db, id)
