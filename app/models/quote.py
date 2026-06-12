# ER-ServiceDesk/app/models/quotes.py
# ORM model for representing service quotes generated from support tickets
#
# The Quote model stores estimated pricing information tied to support
# tickets within the ER‑ServiceDesk system. Quotes allow agents to provide
# customers with cost estimates before work is approved. Each quote tracks
# the amount, optional descriptive details, and creation timestamp.

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# Quote Model
# ---------------------------------------------------------------------------
class Quote(Base):
    __tablename__ = "quotes"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking the quote to a ticket
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    # Estimated amount for the quoted work
    amount = Column(Float, nullable=False)

    # Optional description or breakdown of the quote
    details = Column(Text, nullable=True)

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

    # Relationship back to the Ticket model
    ticket = relationship("Ticket")
