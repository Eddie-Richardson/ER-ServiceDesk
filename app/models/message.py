# ER-ServiceDesk/app/models/message.py
# ORM model for storing inbound and outbound ticket messages
#
# The Message model represents communication exchanged between customers
# and support agents within the ER‑ServiceDesk system. Each message is
# linked to a ticket and optionally to a customer. Messages track direction,
# content, and timestamps for full conversation history.

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# Message Model
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Optional links to ticket and customer
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Message direction: "inbound" (from customer) or "outbound" (from agent/system)
    direction = Column(String, nullable=False)

    # Message body content
    content = Column(Text, nullable=False)

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
    customer = relationship("Customer")
