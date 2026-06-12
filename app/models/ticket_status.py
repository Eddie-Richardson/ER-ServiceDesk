# ER-ServiceDesk/app/models/ticket_statuses.py
# ORM model representing the various statuses a support ticket can have.
#
# The TicketStatus model defines the possible states a ticket may be in,
# such as "Open", "In Progress", or "Resolved". Each status can include
# a color and description for UI display and clarity for support agents.

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# TicketStatus Model
# ---------------------------------------------------------------------------
class TicketStatus(Base):
    __tablename__ = "ticket_statuses"

    id = Column(Integer, primary_key=True, index=True)

    # Name of the status (e.g., "Open", "Closed")
    name = Column(String, unique=True, nullable=False)

    # Optional color code for UI representation
    color = Column(String, nullable=True)

    # Optional description of what this status represents
    description = Column(String, nullable=True)

    # Relationships
    tickets = relationship("Ticket", back_populates="status")
    history = relationship("StatusHistory", back_populates="status")
