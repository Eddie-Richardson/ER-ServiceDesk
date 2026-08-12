# ER-ServiceDesk/app/crud/payment_plan.py
# CRUD operations for PaymentPlan and PaymentPlanInstallment.
"""
Database access layer for a structured installment payment schedule.
"""

from sqlalchemy.orm import Session
from app.models.payment_plan import PaymentPlan
from app.models.payment_plan_installment import PaymentPlanInstallment


class PaymentPlanCRUD:
    """Direct database access for PaymentPlan records."""

    def get(self, db: Session, id: int) -> PaymentPlan | None:
        """
        Fetch a single PaymentPlan by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching PaymentPlan instance, or None if not found.
        """
        return db.query(PaymentPlan).filter(PaymentPlan.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: int) -> PaymentPlan | None:
        """
        Fetch the active payment plan for a given invoice, if any.

        Args:
            db: Active database session.
            invoice_id: The invoice to look up a plan for.

        Returns:
            The matching PaymentPlan instance, or None if this invoice
            has no plan.
        """
        return db.query(PaymentPlan).filter(PaymentPlan.invoice_id == invoice_id).first()

    def create(self, db: Session, invoice_id: int, installment_amount, frequency: str) -> PaymentPlan:
        """
        Insert a new PaymentPlan record.

        Args:
            db: Active database session.
            invoice_id: The invoice this plan is for.
            installment_amount: The per-installment amount entered at setup.
            frequency: "weekly", "biweekly", or "monthly".

        Returns:
            The newly created, refreshed PaymentPlan instance.
        """
        obj = PaymentPlan(invoice_id=invoice_id, installment_amount=installment_amount, frequency=frequency, status="active")
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a PaymentPlan record by primary key, if it exists. Its
        own installments are cascade-deleted with it.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(PaymentPlan).filter(PaymentPlan.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


class PaymentPlanInstallmentCRUD:
    """Direct database access for PaymentPlanInstallment records."""

    def get(self, db: Session, id: int) -> PaymentPlanInstallment | None:
        """
        Fetch a single PaymentPlanInstallment by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching instance, or None if not found.
        """
        return db.query(PaymentPlanInstallment).filter(PaymentPlanInstallment.id == id).first()

    def get_by_plan(self, db: Session, payment_plan_id: int):
        """
        Fetch every installment for a given plan, in schedule order.

        Args:
            db: Active database session.
            payment_plan_id: The plan to look up installments for.

        Returns:
            A list of PaymentPlanInstallment instances, ordered by
            sequence_number.
        """
        return (
            db.query(PaymentPlanInstallment)
            .filter(PaymentPlanInstallment.payment_plan_id == payment_plan_id)
            .order_by(PaymentPlanInstallment.sequence_number)
            .all()
        )

    def create(self, db: Session, payment_plan_id: int, sequence_number: int, due_date, planned_amount) -> PaymentPlanInstallment:
        """
        Insert a new PaymentPlanInstallment record.

        Args:
            db: Active database session.
            payment_plan_id: The plan this installment belongs to.
            sequence_number: This installment's fixed position in the schedule.
            due_date: When this installment is currently due.
            planned_amount: How much is currently expected.

        Returns:
            The newly created, refreshed instance.
        """
        obj = PaymentPlanInstallment(
            payment_plan_id=payment_plan_id, sequence_number=sequence_number,
            due_date=due_date, planned_amount=planned_amount,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a PaymentPlanInstallment record by primary key, if it
        exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(PaymentPlanInstallment).filter(PaymentPlanInstallment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()


crud_payment_plan = PaymentPlanCRUD()
crud_payment_plan_installment = PaymentPlanInstallmentCRUD()
