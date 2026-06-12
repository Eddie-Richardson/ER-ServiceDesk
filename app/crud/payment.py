# ER-ServiceDesk/app/crud/payment.py
# CRUD operations for the Payment model.
#
# Provides database access for creating, reading, updating, and deleting Payment records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

class PaymentCRUD:
    # Retrieves a single Payment by ID.
    def get(self, db: Session, id: int) -> Payment | None:
        """
        Returns a single Payment instance matching the given ID.
        """
        return db.query(Payment).filter(Payment.id == id).first()

    # Retrieves multiple Payment records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Payment records with pagination support.
        """
        return db.query(Payment).offset(skip).limit(limit).all()

    # Creates a new Payment record.
    def create(self, db: Session, obj_in: PaymentCreate) -> Payment:
        """
        Creates a new Payment using the provided input schema.
        """
        obj = Payment(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Payment record.
    def update(self, db: Session, db_obj: Payment, obj_in: PaymentUpdate) -> Payment:
        """
        Updates the given Payment instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Payment record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Payment instance matching the given ID.
        """
        obj = db.query(Payment).filter(Payment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_payment = PaymentCRUD()
