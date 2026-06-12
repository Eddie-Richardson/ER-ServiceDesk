# ER-ServiceDesk/app/models/payments.py
# ORM model for recording invoice payments
#
# The Payment model represents financial transactions applied to invoices
# within the ER‑ServiceDesk system. Each payment stores the amount, method,
# optional transaction reference, and timestamp. Payments are linked to
# invoices through a foreign key and support back-populated relationships.

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# Payment Model
# ---------------------------------------------------------------------------
class Payment(Base):
    __tablename__ = "payments"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking the payment to an invoice
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    # Payment amount
    amount = Column(Float, nullable=False)

    # Payment method (e.g., "credit_card", "cash", "bank_transfer")
    method = Column(String, nullable=False)

    # Optional external transaction reference (e.g., Stripe/PayPal ID)
    transaction_id = Column(String, nullable=True)

    # Timestamp of when the log entry was created
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Timestamp of when the log entry was last updated
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationship back to the Invoice model
    invoice = relationship("Invoice", back_populates="payments")
