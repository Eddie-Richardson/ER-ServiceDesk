# ER-ServiceDesk/app/services/payment_service.py
# Service layer for Payment.
#
# Provides business logic for Payment operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.payment import crud_payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

class PaymentService:
    # Retrieves a single Payment by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Payment instance.
        """
        return crud_payment.get(db, id)

    # Retrieves multiple Payment records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Payment records.
        """
        return crud_payment.get_multi(db, skip, limit)

    # Creates a new Payment.
    def create(self, db: Session, obj_in: PaymentCreate):
        """
        Creates a new Payment using validated input data.
        """
        return crud_payment.create(db, obj_in)

    # Updates an existing Payment.
    def update(self, db: Session, id: int, obj_in: PaymentUpdate):
        """
        Updates an existing Payment using validated input data.
        """
        db_obj = crud_payment.get(db, id)
        return crud_payment.update(db, db_obj, obj_in)

    # Deletes a Payment by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Payment instance.
        """
        return crud_payment.delete(db, id)

payment_service = PaymentService()
