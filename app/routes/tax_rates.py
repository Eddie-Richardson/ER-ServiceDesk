# ER-ServiceDesk/app/routes/tax_rates.py
# API routes for TaxRate operations.
"""
REST endpoints for a named tax rate.

Same gating split as routes/services.py -- GET requires billing.manage,
write operations require superuser specifically.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser, require_permission
from app.models.user import User
from app.services.tax_rate_service import tax_rate_service
from app.schemas.tax_rate import TaxRate, TaxRateCreate, TaxRateUpdate

router = APIRouter(prefix="/tax_rates", tags=["tax_rates"])


@router.get("/", response_model=list[TaxRate], dependencies=[Depends(require_permission("billing.manage"))])
def list_tax_rates(db: Session = Depends(get_db)):
    """List tax rates, paginated."""
    return tax_rate_service.get_multi(db)


@router.get("/{id}", response_model=TaxRate, dependencies=[Depends(require_permission("billing.manage"))])
def get_tax_rate(id: int, db: Session = Depends(get_db)):
    """Fetch a single TaxRate record by ID."""
    return tax_rate_service.get(db, id)


@router.post("/", response_model=TaxRate)
def create_tax_rate(
    obj_in: TaxRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Create a new tax rate. Superuser only."""
    return tax_rate_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=TaxRate)
def update_tax_rate(
    id: int,
    obj_in: TaxRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Update an existing TaxRate, e.g. changing its percentage or deactivating it. Superuser only."""
    return tax_rate_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_tax_rate(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Delete a TaxRate by ID. Superuser only. Safe even if used on existing quotes/invoices -- they keep their own snapshot."""
    return tax_rate_service.delete(db, id, current_user.id)
