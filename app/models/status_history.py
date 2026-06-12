# ER-ServiceDesk/app/models/status_histories.py
# ORM model for tracking changes to a ticket's status over time
#
# The StatusHistory model records every status transition a ticket goes
# through in the ER‑ServiceDesk system. Each entry captures the new status,
# who changed it, and when the change occurred. This provides a complete
# audit trail for ticket lifecycle analysis and compliance.

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from app.db.base import Base

# ---------------------------------------------------------------------------
# StatusHistory Model
# ---------------------------------------------------------------------------
class StatusHistory(Base):
    __tablename__ = "status_history"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("ticket_statuses.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamp of the status change
    changed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="status_history")
    status = relationship("TicketStatus", back_populates="history")
    user = relationship("User")
