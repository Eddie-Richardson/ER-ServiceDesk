# ER-ServiceDesk/app/models/ticket_types.py
# ORM model representing the different categories or classifications of support tickets.
#
# The TicketType model defines how tickets are grouped, such as "Bug Report",
# "Feature Request", or "General Inquiry". This helps organize incoming tickets
# and route them appropriately within the support workflow.

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# TicketType Model
# ---------------------------------------------------------------------------
class TicketType(Base):
    __tablename__ = "ticket_types"

    id = Column(Integer, primary_key=True, index=True)

    # Name of the ticket type (e.g., "Bug", "Request")
    name = Column(String, unique=True, nullable=False)

    # Optional description explaining the purpose of this ticket type
    description = Column(String, nullable=True)

    # Relationships
    tickets = relationship("Ticket", back_populates="type")
