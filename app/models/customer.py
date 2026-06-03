# ER-ServiceDesk/app/models/customer.py
# Customer model for storing client information
#
# Represents a customer within the ER‑ServiceDesk system. Customers may own
# multiple devices and may have multiple support tickets associated with them.
# This model stores identifying and contact information for each customer.
# It is used throughout the system for ticket creation, device assignment,
# and customer‑facing communication workflows.

# ---------------------------------------------------------------------------
# Customer Model
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    # Unique identifier for the customer
    id = Column(Integer, primary_key=True, index=True)

    # Customer's first and last name
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    # Contact information
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

    # Timestamp for when the customer record was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    devices = relationship("Device", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
