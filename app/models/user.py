# ER-ServiceDesk/app/models/user.py
# User model representing system accounts and authentication identities
#
# Represents a user within the ER‑ServiceDesk platform. Users authenticate
# into the system, may be assigned one or more roles, and can interact with
# various system components such as tickets and internal notes. This model
# stores authentication credentials, profile information, and status flags
# used throughout the authorization and account‑management workflows.

# ---------------------------------------------------------------------------
# User Model
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Unique identifier for the user
    id = Column(Integer, primary_key=True, index=True)

    # Login and authentication fields
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)

    # Optional profile information
    full_name = Column(String, nullable=True)

    # Account status flags
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Timestamp for when the user account was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    roles = relationship("UserRole", back_populates="user")
    notes = relationship("Note", back_populates="user")
    tickets_assigned = relationship("Ticket", back_populates="assigned_to_user")
