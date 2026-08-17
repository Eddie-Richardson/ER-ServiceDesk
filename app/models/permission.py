# ER-ServiceDesk/app/models/permission.py
# ORM model for a single grantable capability in the RBAC system
"""
ORM model for a single grantable capability in the RBAC system.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Permission(Base):
    """
    Represents one capability (e.g. 'ticket.create') that can be assigned to roles.

    Attributes:
        name: Unique permission identifier (e.g. 'view_reports').
    """
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    role_permissions = relationship("RolePermission", back_populates="permission")
