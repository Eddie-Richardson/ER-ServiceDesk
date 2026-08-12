# ER-ServiceDesk/app/routes/discounts.py
# API routes for Discount operations.
"""
REST endpoints for a named discount category.

Same gating split as routes/services.py -- GET requires billing.manage,
write operations require superuser specifically.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser, require_permission
from app.models.user import User
from app.services.discount_service import discount_service
from app.schemas.discount import Discount, DiscountCreate, DiscountUpdate

router = APIRouter(prefix="/discounts", tags=["discounts"])


@router.get("/", response_model=list[Discount], dependencies=[Depends(require_permission("billing.manage"))])
def list_discounts(db: Session = Depends(get_db)):
    """List discounts, paginated."""
    return discount_service.get_multi(db)


@router.get("/{id}", response_model=Discount, dependencies=[Depends(require_permission("billing.manage"))])
def get_discount(id: int, db: Session = Depends(get_db)):
    """Fetch a single Discount record by ID."""
    return discount_service.get(db, id)


@router.post("/", response_model=Discount)
def create_discount(
    obj_in: DiscountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Create a new discount category. Superuser only."""
    return discount_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=Discount)
def update_discount(
    id: int,
    obj_in: DiscountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Update an existing Discount, e.g. changing its percentage or deactivating it. Superuser only."""
    return discount_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_discount(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Delete a Discount by ID. Superuser only. Safe even if used on existing quotes/invoices -- they keep their own snapshot."""
    return discount_service.delete(db, id, current_user.id)
