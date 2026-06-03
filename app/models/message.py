# ER-ServiceDesk/app/models/message.py
# ORM model for storing inbound and outbound ticket messages
#
# The Message model represents communication exchanged between customers
# and support agents within the ER‑ServiceDesk system. Each message is
# linked to a ticket and optionally to a customer. Messages track direction,
# content, and timestamps for full conversation history.

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# Message Model
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Optional links to ticket and customer
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # Message direction: "inbound" (from customer) or "outbound" (from agent/system)
    direction = Column(String, nullable=False)

    # Message body content
    content = Column(Text, nullable=False)

    # Timestamp when the message was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket")
    customer = relationship("Customer")
