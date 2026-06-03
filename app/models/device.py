# ER-ServiceDesk/app/models/device.py
# ORM model representing customer‑owned devices associated with support tickets.
#
# The Device model stores hardware information such as type, brand, model,
# and serial number. Devices are linked to customers and may be referenced
# by support tickets for troubleshooting, history tracking, and reporting.

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# Device Model
# ---------------------------------------------------------------------------
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    # Customer who owns the device
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Device classification (e.g., "Laptop", "Router")
    device_type = Column(String, nullable=False)

    # Optional brand name (e.g., "Dell", "Apple")
    brand = Column(String, nullable=True)

    # Optional model identifier
    model = Column(String, nullable=True)

    # Optional serial number for asset tracking
    serial_number = Column(String, nullable=True)

    # Timestamp when the device record was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="devices")
    tickets = relationship("Ticket", back_populates="device")
