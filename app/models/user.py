# ER-ServiceDesk/app/models/user.py
"""
ORM model for staff/system accounts and their authentication identity.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class User(Base):
    """
    Represents a staff account: authentication credentials, profile info,
    and status flags used throughout authorization and account management.

    Attributes:
        hashed_password: Bcrypt hash of the account password. Never exposed
            in API responses -- see app.schemas.user for the response schema.
        is_active: Whether the account can currently log in.
        is_superuser: Whether the account has unrestricted admin access.
        must_change_password: True whenever the current password was
            set by an admin (new account, or a password reset) rather
            than chosen by the user themselves. Login is blocked (no
            token issued) until they change it via
            POST /auth/change-password -- see app.routes.auth.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    roles = relationship("UserRole", back_populates="user")
    tickets_assigned = relationship("Ticket", back_populates="assigned_to_user")

    @property
    def full_name(self):
        """Return the user's first and last name joined with a space."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_front_desk(self) -> bool:
        """Whether this user has the front_desk role. Front desk can assign tickets to agents, but should never be an assignment target themselves -- see AssignableUser."""
        return any(user_role.role.name == "front_desk" for user_role in self.roles)
