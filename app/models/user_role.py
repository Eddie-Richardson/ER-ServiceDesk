# ER-ServiceDesk/app/models/user_role.py
"""
ORM model for the many-to-many link between users and roles.
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserRole(Base):
    """
    Join record granting a single role to a single user.
    """
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")
