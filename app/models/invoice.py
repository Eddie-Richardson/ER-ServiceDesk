# ER-ServiceDesk/app/models/invoice.py
# ORM model for a bill generated for work performed on a ticket
"""
ORM model for a bill generated for work performed on a ticket.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Invoice(Base):
    """
    Represents a billing record tied to a ticket, tracking amount owed and payment status.

    Attributes:
        id: Primary key.
        ticket_id: The ticket this invoice bills for.
        amount: Total invoice amount.
        details: Optional description or line-item breakdown.
        is_paid: Whether the invoice has been fully paid.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    details = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket")
    payments = relationship("Payment", back_populates="invoice")
