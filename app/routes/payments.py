# ER-ServiceDesk/app/routes/payments.py
# API routes for Payment operations.
"""
REST endpoints for a payment applied against an invoice.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.payment_service import payment_service
from app.schemas.payment import Payment, PaymentCreate, PaymentUpdate

router = APIRouter(prefix="/payments", tags=["payments"])

@router.get("/", response_model=list[Payment])
def list_payments(db: Session = Depends(get_db)):
    """
    List a payment applied against an invoice, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Payment records.
    """
    return payment_service.get_multi(db)

@router.get("/{id}", response_model=Payment)
def get_payment(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Payment record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Payment record.
    """
    return payment_service.get(db, id)

@router.post("/", response_model=Payment)
def create_payment(obj_in: PaymentCreate, db: Session = Depends(get_db)):
    """
    Create a new Payment record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Payment record.
    """
    return payment_service.create(db, obj_in)

@router.put("/{id}", response_model=Payment)
def update_payment(id: int, obj_in: PaymentUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Payment record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Payment record.
    """
    return payment_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_payment(id: int, db: Session = Depends(get_db)):
    """
    Delete a Payment record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return payment_service.delete(db, id)
