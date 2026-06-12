# ER-ServiceDesk/app/models/ticket_categories.py
# ORM model representing the high‑level grouping of support tickets.
#
# The TicketCategory model defines broad organizational buckets such as
# "Hardware", "Software", or "Network". Categories help segment tickets
# for reporting, routing, and workload distribution across support teams.

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# TicketCategory Model
# ---------------------------------------------------------------------------
class TicketCategory(Base):
    __tablename__ = "ticket_categories"

    id = Column(Integer, primary_key=True, index=True)

    # Name of the category (e.g., "Network", "Hardware")
    name = Column(String, unique=True, nullable=False)

    # Optional description explaining what falls under this category
    description = Column(String, nullable=True)

    # Relationships
    tickets = relationship("Ticket", back_populates="category")
