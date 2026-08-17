# ER-ServiceDesk/app/models/device_user_account.py
# ORM model for a login account known to exist on a device
"""
ORM model for a login account known to exist on a device -- the
"Login Information" section of the drop-off form, made into a real
expandable list (a device can have more than one account, though
usually just one or two) rather than the two fixed slots on the paper
form.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base


class DeviceUserAccount(Base):
    """
    Represents one login account known to exist on a device.

    Attributes:
        device_id: Device-level, not Ticket-level -- these rarely
            change between repairs on the same machine.
        encrypted_password: The account's password, encrypted at rest
            (see app/core/encryption.py) -- NOT one-way hashed like a
            login password, since this needs to be shown back to a
            tech viewing the customer's profile. Increasingly a
            Microsoft account password (the same credential unlocking
            email/OneDrive/etc.), not just a local Windows login, which
            is why real reversible encryption matters here more than
            it might otherwise.
    """
    __tablename__ = "device_user_accounts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    account_name = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    device = relationship("Device", back_populates="user_accounts")
