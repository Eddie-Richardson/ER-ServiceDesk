# ER-ServiceDesk/app/models/ticket.py
# ORM model representing support tickets within the ER‑ServiceDesk system.
#
# Tickets link customers, devices, categories, types, statuses, assigned
# technicians, and related communication/history records. This is the core
# entity of the helpdesk workflow.

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# Ticket Model
# ---------------------------------------------------------------------------
class Ticket(Base):
    __tablename__ = "tickets"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False)
    type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("ticket_statuses.id"), nullable=False)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Ticket content
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    device = relationship("Device", back_populates="tickets")
    category = relationship("TicketCategory", back_populates="tickets")
    type = relationship("TicketType", back_populates="tickets")
    status = relationship("TicketStatus", back_populates="tickets")
    assigned_to_user = relationship("User", back_populates="tickets_assigned")

    # Notes attached to this ticket (internal or customer-visible)
    notes = relationship("Note", back_populates="ticket")

    status_history = relationship("StatusHistory", back_populates="ticket")
