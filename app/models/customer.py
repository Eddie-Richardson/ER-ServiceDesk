# ER-ServiceDesk/app/models/customer.py
# ORM model for a client of the repair shop
"""
ORM model for a client of the repair shop.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Customer(Base):
    """
    Represents a customer who owns devices and may have one or more support tickets open.

    Attributes:
        email: Unique contact email, used for ticket notifications.
        is_archived: Hidden from the active ticket picker and the
            default Customers view once True -- set either manually
            (Archive/Unarchive in the Customers window) or
            automatically once a customer crosses the inactivity
            threshold (see app.workers.tasks.archive_inactive_customers).
            Fully reversible; doesn't delete or hide anything else
            about the customer, still findable and editable in the
            Customers window with the "Show Archived" filter on.
    """
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    street = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    devices = relationship("Device", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
