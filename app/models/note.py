# ER-ServiceDesk/app/models/note.py
# ORM model for internal and customer-visible notes on support tickets
#
# The Note model stores annotations linked to support tickets. Notes may be
# internal (visible only to support agents) or public (visible to customers).
# This allows agents to collaborate privately while still sharing relevant
# updates with customers.

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# Note Model
# ---------------------------------------------------------------------------
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Whether the note is visible to the customer
    is_public = Column(Boolean, default=False)

    # Note content
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
    ticket = relationship("Ticket", back_populates="notes")
    user = relationship("User", back_populates="notes")
