# ER-ServiceDesk/app/routes/services.py
# API routes for Service (billable-service catalog) operations.
"""
REST endpoints for a billable service the shop offers.

GET routes require billing.manage -- the person doing billing needs to
see this list to pick from when building a quote/invoice's line
items. Write routes (create/update/delete) require superuser
specifically, since they control actual pricing -- a meaningfully
more sensitive action than just viewing the current price list.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser, require_permission
from app.models.user import User
from app.services.service_service import service_service
from app.schemas.service import Service, ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/", response_model=list[Service], dependencies=[Depends(require_permission("billing.manage"))])
def list_services(db: Session = Depends(get_db)):
    """List billable services, paginated."""
    return service_service.get_multi(db)


@router.get("/{id}", response_model=Service, dependencies=[Depends(require_permission("billing.manage"))])
def get_service(id: int, db: Session = Depends(get_db)):
    """Fetch a single Service record by ID."""
    return service_service.get(db, id)


@router.post("/", response_model=Service)
def create_service(
    obj_in: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Create a new billable service. Superuser only."""
    return service_service.create(db, obj_in, current_user.id)


@router.put("/{id}", response_model=Service)
def update_service(
    id: int,
    obj_in: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Update an existing Service, e.g. changing its price or deactivating it. Superuser only."""
    return service_service.update(db, id, obj_in, current_user.id)


@router.delete("/{id}")
def delete_service(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Delete a Service by ID. Superuser only. Safe even if used on existing quotes/invoices -- they keep their own snapshot."""
    return service_service.delete(db, id, current_user.id)
