# ER-ServiceDesk/app/crud/payment.py
# CRUD operations for the Payment model.
"""
Database access layer for a payment applied against an invoice.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

class PaymentCRUD:
    """Direct database access for Payment records."""

    def get(self, db: Session, id: int) -> Payment | None:
        """
        Fetch a single Payment by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Payment instance, or None if no record exists.
        """
        return db.query(Payment).filter(Payment.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Payment records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Payment instances.
        """
        return db.query(Payment).offset(skip).limit(limit).all()

    def get_by_invoice(self, db: Session, invoice_id: int):
        """
        Fetch every payment recorded against a given invoice.

        Args:
            db: Active database session.
            invoice_id: The invoice to look up payments for.

        Returns:
            A list of Payment instances for that invoice.
        """
        return db.query(Payment).filter(Payment.invoice_id == invoice_id).all()

    def create(self, db: Session, obj_in: PaymentCreate) -> Payment:
        """
        Insert a new Payment record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Payment instance.
        """
        obj = Payment(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Payment, obj_in: PaymentUpdate) -> Payment:
        """
        Apply a partial update to an existing Payment record.

        Args:
            db: Active database session.
            db_obj: The existing Payment instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Payment instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Payment record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Payment).filter(Payment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_payment = PaymentCRUD()
