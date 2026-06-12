# ER-ServiceDesk/app/app/models/role_permissions.py
# Role ↔ Permission join table
#
# This model represents the many-to-many relationship between roles
# and permissions. Each row links a single role to a single permission.
# It fits into the authorization layer of the system.

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# Model: RolePermission
# ---------------------------------------------------------------------------

# Fields:
#     id (int) - Primary key
#     role_id (int) - FK to Role.id
#     permission_id (int) - FK to Permission.id
#
# Relationships:
#     role - Parent role
#     permission - Parent permission

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
