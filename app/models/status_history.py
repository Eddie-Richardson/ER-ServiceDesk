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

    @property
    def status_name(self) -> str | None:
        """
        Returns:
            The related TicketStatus's display name, or None if
            somehow unset. Denormalized so the API response can
            include it directly (see schemas/status_history.py),
            avoiding a separate /ticket_statuses/ lookup just to show
            what a history entry actually changed to.
        """
        return self.status.name if self.status else None

    @property
    def changed_by_name(self) -> str | None:
        """
        Returns:
            The user who made this change's display name, or None if
            somehow unset. Denormalized for the same reason as
            status_name above.
        """
        return self.user.full_name if self.user else None
