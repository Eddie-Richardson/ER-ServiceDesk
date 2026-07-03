# ER-ServiceDesk/app/models/status_history.py
# ORM model for an audit trail entry for a ticket status transition
"""
ORM model for an audit trail entry for a ticket status transition.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class StatusHistory(Base):
    """
    Represents a single status change on a ticket: what it changed to, who changed it, and when.

    Attributes:
        id: Primary key.
        ticket_id: The ticket whose status changed.
        status_id: The new status.
        changed_by: The user who made the change.
        changed_at: Timestamp of the status change.
    """
    __tablename__ = "status_history"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("ticket_statuses.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket", back_populates="status_history")
    status = relationship("TicketStatus", back_populates="history")
    user = relationship("User")
