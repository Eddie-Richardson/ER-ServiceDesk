# ER-ServiceDesk/app/routes/customers.py
# API routes for Customer operations.
#
# Exposes REST endpoints for interacting with Customer records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.customer_service import customer_service
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/", response_model=list[Customer])
def list_customers(db: Session = Depends(get_db)):
    """
    Returns a list of Customer records.
    """
    return customer_service.get_multi(db)

@router.get("/{id}", response_model=Customer)
def get_customer(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Customer record by ID.
    """
    return customer_service.get(db, id)

@router.post("/", response_model=Customer)
def create_customer(obj_in: CustomerCreate, db: Session = Depends(get_db)):
    """
    Creates a new Customer record.
    """
    return customer_service.create(db, obj_in)

@router.put("/{id}", response_model=Customer)
def update_customer(id: int, obj_in: CustomerUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Customer record.
    """
    return customer_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_customer(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Customer record by ID.
    """
    return customer_service.delete(db, id)
