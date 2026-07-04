# ER-ServiceDesk/app/models/ticket_type.py
# ORM model for a classification of the kind of work a ticket represents
"""
ORM model for a classification of the kind of work a ticket represents.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class TicketType(Base):
    """
    Represents a ticket classification (e.g. 'Bug Report', 'Feature Request') used for routing.

    Attributes:
        id: Primary key.
        name: Unique type name.
        description: Optional explanation of this ticket type.
    """
    __tablename__ = "ticket_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    tickets = relationship("Ticket", back_populates="type")
    allowed_stages = relationship("TicketTypeStage", back_populates="ticket_type")
