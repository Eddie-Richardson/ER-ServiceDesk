# ER-ServiceDesk/app/models/device.py
# ORM model for a customer-owned device brought in for service
"""
ORM model for a customer-owned device brought in for service.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Device(Base):
    """
    Represents a piece of hardware owned by a customer, referenced by support tickets.

    Attributes:
        id: Primary key.
        customer_id: The customer who owns this device.
        device_type: Classification of the device (e.g. 'Laptop', 'Router').
        brand: Optional manufacturer/brand name.
        model: Optional model identifier.
        serial_number: Optional serial number for asset tracking.
        current_location_id: Where this device is physically located in
            the shop right now (e.g. a bench, a shelf).
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    device_type = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    current_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    customer = relationship("Customer", back_populates="devices")
    tickets = relationship("Ticket", back_populates="device")
    current_location = relationship("Location", back_populates="devices")
