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
        return db.query(Payment).filter(Payment.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Payment).offset(skip).limit(limit).all()

    def get_by_invoice(self, db: Session, invoice_id: int):
        return db.query(Payment).filter(Payment.invoice_id == invoice_id).all()

    def create(self, db: Session, obj_in: PaymentCreate) -> Payment:
        obj = Payment(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Payment, obj_in: PaymentUpdate) -> Payment:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Payment).filter(Payment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_payment = PaymentCRUD()
