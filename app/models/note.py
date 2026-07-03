# ER-ServiceDesk/app/models/note.py
# ORM model for an internal or customer-visible annotation on a ticket
"""
ORM model for an internal or customer-visible annotation on a ticket.
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Note(Base):
    """
    Represents a note left on a ticket, either private to staff or visible to the customer.

    Attributes:
        id: Primary key.
        ticket_id: The ticket this note is attached to.
        user_id: The staff member who wrote the note.
        is_public: Whether the note is visible to the customer.
        content: The note body.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket", back_populates="notes")
    user = relationship("User", back_populates="notes")
