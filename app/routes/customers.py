# ER-ServiceDesk/app/routes/customers.py
# API routes for Customer operations.
"""
REST endpoints for a client of the repair shop.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.customer_service import customer_service
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(require_permission("customers.manage"))])

@router.get("/", response_model=list[Customer])
def list_customers(db: Session = Depends(get_db)):
    """
    List a client of the repair shop, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Customer records.
    """
    return customer_service.get_multi(db)

@router.get("/{id}", response_model=Customer)
def get_customer(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Customer record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Customer record.
    """
    return customer_service.get(db, id)

@router.post("/", response_model=Customer)
def create_customer(
    obj_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new Customer record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.
        current_user: The user creating this record -- recorded in
            the audit trail.

    Returns:
        The newly created Customer record.
    """
    return customer_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=Customer)
def update_customer(
    id: int,
    obj_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing Customer record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.
        current_user: The user making this change -- recorded in the
            audit trail.

    Returns:
        The updated Customer record.
    """
    return customer_service.update(db, id, obj_in, current_user.id)

@router.delete("/{id}")
def delete_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a Customer record by ID, if they have zero tickets and zero
    devices on file.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
        current_user: The user performing this deletion -- recorded
            in the audit trail.

    Raises:
        HTTPException: 400 if this customer has any tickets or devices
            on file.
    """
    return customer_service.delete(db, id, current_user.id)

@router.post("/{id}/archive", response_model=Customer)
def archive_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Archive a customer -- hides them from the active ticket picker and
    the default Customers view. Fully reversible.

    Args:
        id: Primary key of the customer to archive.
        db: Injected database session.
        current_user: The user archiving this customer -- recorded in
            the audit trail.

    Returns:
        The updated Customer record.
    """
    return customer_service.archive(db, id, current_user.id)

@router.post("/{id}/unarchive", response_model=Customer)
def unarchive_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reverse archive_customer().

    Args:
        id: Primary key of the customer to unarchive.
        db: Injected database session.
        current_user: The user unarchiving this customer -- recorded
            in the audit trail.

    Returns:
        The updated Customer record.
    """
    return customer_service.unarchive(db, id, current_user.id)
