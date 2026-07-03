# ER-ServiceDesk/app/models/message.py
# ORM model for a customer-facing message exchanged on a ticket (e.g. via email)
"""
ORM model for a customer-facing message exchanged on a ticket (e.g. via email).
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Message(Base):
    """
    Represents a single inbound or outbound message in the conversation thread for a ticket.

    Attributes:
        id: Primary key.
        ticket_id: The ticket this message belongs to.
        customer_id: The customer this message was sent to/received from.
        direction: 'inbound' (from customer) or 'outbound' (from agent/system).
        content: The message body.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    direction = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket")
    customer = relationship("Customer")
