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
from app.services.customer_service import customer_service
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

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
def create_customer(obj_in: CustomerCreate, db: Session = Depends(get_db)):
    """
    Create a new Customer record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Customer record.
    """
    return customer_service.create(db, obj_in)

@router.put("/{id}", response_model=Customer)
def update_customer(id: int, obj_in: CustomerUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Customer record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Customer record.
    """
    return customer_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_customer(id: int, db: Session = Depends(get_db)):
    """
    Delete a Customer record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return customer_service.delete(db, id)
