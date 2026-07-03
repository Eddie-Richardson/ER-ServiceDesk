# ER-ServiceDesk/app/models/customer.py
# ORM model for a client of the repair shop
"""
ORM model for a client of the repair shop.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Customer(Base):
    """
    Represents a customer who owns devices and may have one or more support tickets open.

    Attributes:
        id: Primary key.
        first_name: Customer's first name.
        last_name: Customer's last name.
        email: Unique contact email, used for ticket notifications.
        phone: Optional contact phone number.
        address: Optional mailing/service address.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    devices = relationship("Device", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
