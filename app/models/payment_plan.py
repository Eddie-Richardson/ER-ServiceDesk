# ER-ServiceDesk/app/models/payment_plan.py
# ORM model for a structured installment payment schedule on an invoice
"""
ORM model for a structured installment payment schedule on an invoice.

Set up with a per-installment amount and a frequency (weekly/
biweekly/monthly) -- the number of installments and their due dates
are worked out from that, not entered directly. See
payment_plan_service.py for the full setup, payment-recording (with
automatic rebalancing), and date-extension logic.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base


class PaymentPlan(Base):
    """
    Represents a structured installment payment schedule on an invoice.

    Attributes:
        id: Primary key.
        invoice_id: The invoice this payment plan is for. One active
            plan per invoice.
        installment_amount: The original per-installment amount
            entered at setup (e.g. 20.00) -- kept as a reference even
            though individual installments' actual planned amounts
            may later change via rebalancing.
        frequency: How often installments are due -- "weekly",
            "biweekly", or "monthly".
        status: "active" while payments are still being collected,
            "completed" once the balance reaches zero.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "payment_plans"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    installment_amount = Column(Numeric, nullable=False)
    frequency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    invoice = relationship("Invoice")
    installments = relationship("PaymentPlanInstallment", back_populates="payment_plan", cascade="all, delete-orphan", order_by="PaymentPlanInstallment.sequence_number")
