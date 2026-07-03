# ER-ServiceDesk/app/services/payment_service.py
# Service layer for Payment.
"""
Business logic for a payment applied against an invoice.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.payment import crud_payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

class PaymentService:
    """Business logic for Payment operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Payment by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Payment instance, or None if not found.
        """
        return crud_payment.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Payment records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Payment instances.
        """
        return crud_payment.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PaymentCreate):
        """
        Create a new Payment using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Payment instance.
        """
        return crud_payment.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: PaymentUpdate):
        """
        Update an existing Payment using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Payment instance.
        """
        db_obj = crud_payment.get(db, id)
        return crud_payment.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Payment by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_payment.delete(db, id)

payment_service = PaymentService()
