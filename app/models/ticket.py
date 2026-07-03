# ER-ServiceDesk/app/models/ticket.py
# ORM model for a support/repair job tracked from intake to completion
"""
ORM model for a support/repair job tracked from intake to completion.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Ticket(Base):
    """
    Represents the core workflow entity: a device brought in by a customer, tracked through category, type, status, and technician assignment.

    Attributes:
        id: Primary key.
        customer_id: The customer this ticket is for.
        device_id: The device being serviced.
        category_id: High-level grouping (e.g. Hardware, Software).
        type_id: Classification (e.g. Bug, Repair Request).
        status_id: Current workflow status.
        assigned_to: The technician assigned to this ticket, if any.
        title: Short summary of the issue.
        description: Optional full description of the issue.
        priority: Ticket priority level.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False)
    type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("ticket_statuses.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    customer = relationship("Customer", back_populates="tickets")
    device = relationship("Device", back_populates="tickets")
    category = relationship("TicketCategory", back_populates="tickets")
    type = relationship("TicketType", back_populates="tickets")
    status = relationship("TicketStatus", back_populates="tickets")
    assigned_to_user = relationship("User", back_populates="tickets_assigned")
    notes = relationship("Note", back_populates="ticket")
    status_history = relationship("StatusHistory", back_populates="ticket")
