# ER-ServiceDesk/app/models/quote.py
# ORM model for representing service quotes generated from support tickets
#
# The Quote model stores estimated pricing information tied to support
# tickets within the ER‑ServiceDesk system. Quotes allow agents to provide
# customers with cost estimates before work is approved. Each quote tracks
# the amount, optional descriptive details, and creation timestamp.

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

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

    # Timestamp when the quote was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to the Ticket model
    ticket = relationship("Ticket")
