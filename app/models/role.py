# ER-ServiceDesk/app/models/role.py
# ORM model for an authorization grouping assigned to users
"""
ORM model for an authorization grouping assigned to users.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Role(Base):
    """
    Represents a named collection of permissions that can be assigned to users.

    Attributes:
        name: Unique role name (e.g. 'admin', 'agent').
    """
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    users = relationship("UserRole", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role")
