# ER-ServiceDesk/app/models/ticket_status.py
"""
ORM model for a workflow state a ticket can occupy.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class TicketStatus(Base):
    """
    Represents a possible ticket state (e.g. 'Open', 'In Progress', 'Resolved').
    """
    __tablename__ = "ticket_statuses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    tickets = relationship("Ticket", back_populates="status")
    history = relationship("StatusHistory", back_populates="status")
