# ER-ServiceDesk/app/models/ticket_stage.py
# ORM model for the granular repair/build stage a ticket is at
"""
ORM model for tracking the specific step of work a ticket is on, distinct
from its high-level TicketStatus. Covers both repair tickets (e.g.
"Diagnosing", "Awaiting Parts", "Testing") and custom build orders (e.g.
"Assembling", "OS Install", "Burn-in Test", "QC").
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class TicketStage(Base):
    """
    Represents a single granular stage of work a ticket can be at.

    Attributes:
        id: Primary key.
        name: Unique stage name (e.g. "Diagnosing", "Burn-in Test").
        description: Optional explanation of what this stage covers.
    """
    __tablename__ = "ticket_stages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    tickets = relationship("Ticket", back_populates="stage")
    allowed_for_types = relationship("TicketTypeStage", back_populates="stage")
