# ER-ServiceDesk/app/models/payment.py
# ORM model for a payment applied against an invoice
"""
ORM model for a payment applied against an invoice.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Payment(Base):
    """
    Represents a single financial transaction applied to an invoice.

    Attributes:
        id: Primary key.
        invoice_id: The invoice this payment applies to.
        amount: Payment amount.
        method: Payment method (e.g. 'credit_card', 'cash').
        transaction_id: Optional external processor reference (e.g. Stripe ID).
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    transaction_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    invoice = relationship("Invoice", back_populates="payments")
