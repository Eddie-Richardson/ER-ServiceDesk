# ER-ServiceDesk/app/models/ticket_stage.py
"""
ORM model for a granular step of work a ticket can be assigned, more
specific than its high-level TicketStatus. Which stages are valid for
a given ticket depends on its type -- see TicketTypeStage.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class TicketStage(Base):
    """
    Represents a single granular stage of work a ticket can be at.
    """
    __tablename__ = "ticket_stages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    tickets = relationship("Ticket", back_populates="stage")
    allowed_for_types = relationship("TicketTypeStage", back_populates="stage")
