# ER-ServiceDesk/app/crud/payment_plan.py
"""
Database access layer for a structured installment payment schedule.
"""

from sqlalchemy.orm import Session
from app.models.payment_plan import PaymentPlan
from app.models.payment_plan_installment import PaymentPlanInstallment


class PaymentPlanCRUD:
    """Direct database access for PaymentPlan records."""

    def get(self, db: Session, id: int) -> PaymentPlan | None:
        return db.query(PaymentPlan).filter(PaymentPlan.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: int) -> PaymentPlan | None:
        return db.query(PaymentPlan).filter(PaymentPlan.invoice_id == invoice_id).first()

    def create(self, db: Session, invoice_id: int, installment_amount, frequency: str) -> PaymentPlan:
        obj = PaymentPlan(invoice_id=invoice_id, installment_amount=installment_amount, frequency=frequency, status="active")
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        """Its own installments are cascade-deleted with it."""
        obj = db.query(PaymentPlan).filter(PaymentPlan.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


class PaymentPlanInstallmentCRUD:
    """Direct database access for PaymentPlanInstallment records."""

    def get(self, db: Session, id: int) -> PaymentPlanInstallment | None:
        return db.query(PaymentPlanInstallment).filter(PaymentPlanInstallment.id == id).first()

    def get_by_plan(self, db: Session, payment_plan_id: int):
        """Returned in schedule order (by sequence_number), not insertion or id order."""
        return (
            db.query(PaymentPlanInstallment)
            .filter(PaymentPlanInstallment.payment_plan_id == payment_plan_id)
            .order_by(PaymentPlanInstallment.sequence_number)
            .all()
        )

    def create(self, db: Session, payment_plan_id: int, sequence_number: int, due_date, planned_amount) -> PaymentPlanInstallment:
        obj = PaymentPlanInstallment(
            payment_plan_id=payment_plan_id, sequence_number=sequence_number,
            due_date=due_date, planned_amount=planned_amount,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(PaymentPlanInstallment).filter(PaymentPlanInstallment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


crud_payment_plan = PaymentPlanCRUD()
crud_payment_plan_installment = PaymentPlanInstallmentCRUD()
