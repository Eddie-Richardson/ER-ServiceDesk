# ER-ServiceDesk/app/models/invoices.py
# ORM model for representing invoices generated from support tickets
#
# The Invoice model stores billing information tied to support tickets
# within the ER‑ServiceDesk system. Each invoice tracks the billed amount,
# optional descriptive details, payment status, and creation timestamp.
# Invoices maintain a relationship to their associated payments.

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# Invoice Model
# ---------------------------------------------------------------------------
class Invoice(Base):
    __tablename__ = "invoices"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking the invoice to a ticket
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    # Total invoice amount
    amount = Column(Float, nullable=False)

    # Optional description or line‑item details
    details = Column(Text, nullable=True)

    # Whether the invoice has been fully paid
    is_paid = Column(Boolean, default=False)

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

    # Relationships
    ticket = relationship("Ticket")
    payments = relationship("Payment", back_populates="invoice")
