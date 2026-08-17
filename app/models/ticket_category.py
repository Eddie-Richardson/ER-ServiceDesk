# ER-ServiceDesk/app/models/ticket_category.py
# ORM model for a high-level grouping used to organize tickets
"""
ORM model for a high-level grouping used to organize tickets.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class TicketCategory(Base):
    """
    Represents a broad organizational bucket for tickets (e.g. 'Hardware', 'Network').
    """
    __tablename__ = "ticket_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    tickets = relationship("Ticket", back_populates="category")
