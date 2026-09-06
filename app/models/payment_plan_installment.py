# ER-ServiceDesk/app/models/payment_plan_installment.py
"""
ORM model for a single scheduled installment within a payment plan.
"""

from sqlalchemy import Column, Integer, Numeric, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


class PaymentPlanInstallment(Base):
    """
    Represents one scheduled installment within a payment plan.

    Attributes:
        sequence_number: This installment's fixed position in the
            schedule (1, 2, 3...) -- kept separate from due_date since
            due_date can be manually changed later (see
            payment_plan_service.extend_installment_date()), and later
            installments need a stable way to know their own order
            relative to each other regardless of date edits.
        due_date: When this installment is currently scheduled to be paid.
        planned_amount: How much is currently expected for this
            installment -- the original evenly-worked-out amount,
            unless it's since been rebalanced due to an over/under
            payment on an earlier installment.
        payment_id: The actual Payment record, once this installment
            has been paid -- null while still outstanding. The actual
            amount paid may differ from planned_amount (a customer
            paying more or less than planned is exactly what triggers
            rebalancing the remaining installments).
    """
    __tablename__ = "payment_plan_installments"
    id = Column(Integer, primary_key=True, index=True)
    payment_plan_id = Column(Integer, ForeignKey("payment_plans.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    planned_amount = Column(Numeric, nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)

    payment_plan = relationship("PaymentPlan", back_populates="installments")
    payment = relationship("Payment")
