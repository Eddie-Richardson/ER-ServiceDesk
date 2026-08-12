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
        stage_id: Granular step of work (e.g. "Diagnosing" for a repair,
            "Burn-in Test" for a custom build). Distinct from status_id,
            which stays at the high-level Open/In Progress/Resolved axis.
        assigned_to: The technician assigned to this ticket, if any.
        current_location_id: Where the device physically is right now
            (e.g. a bench, a shelf, shipped to customer).
        title: Short summary of the issue.
        description: Optional full description of the issue.
        priority: Ticket priority level.
        pickup_person: Who is authorized to pick up the device for this
            particular visit -- varies per ticket, not a fixed
            Customer-level fact (a different person could drop off and
            pick up, or pick-up person could differ across repeat
            repairs for the same customer).
        accessories_included: What was physically brought in with the
            device at drop-off for this visit (e.g. "charger, no bag")
            -- also varies per visit, not a permanent Device fact.
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
    stage_id = Column(Integer, ForeignKey("ticket_stages.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    current_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=False, index=True)
    pickup_person = Column(String, nullable=True)
    accessories_included = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    customer = relationship("Customer", back_populates="tickets")
    device = relationship("Device", back_populates="tickets")
    category = relationship("TicketCategory", back_populates="tickets")
    type = relationship("TicketType", back_populates="tickets")
    status = relationship("TicketStatus", back_populates="tickets")
    stage = relationship("TicketStage", back_populates="tickets")
    assigned_to_user = relationship("User", back_populates="tickets_assigned")
    status_history = relationship("StatusHistory", back_populates="ticket")
    current_location = relationship("Location", back_populates="tickets")
    parts_needed = relationship("TicketPart", back_populates="ticket")
