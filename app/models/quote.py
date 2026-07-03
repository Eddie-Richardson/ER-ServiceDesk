# ER-ServiceDesk/app/models/quote.py
# ORM model for an estimated price for ticket-related work, pending customer approval
"""
ORM model for an estimated price for ticket-related work, pending customer approval.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Quote(Base):
    """
    Represents a cost estimate given to a customer before work is approved.

    Attributes:
        id: Primary key.
        ticket_id: The ticket this quote is for.
        amount: Estimated amount for the quoted work.
        details: Optional description or breakdown of the quote.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket")
