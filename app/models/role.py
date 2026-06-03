# ER-ServiceDesk/app/models/role.py
# Role model representing authorization groupings
#
# Represents a role within the ER‑ServiceDesk RBAC (Role-Based Access Control)
# system. Roles define collections of permissions that determine what actions
# a user is allowed to perform. Users may have multiple roles, and roles may
# be assigned to many users through the UserRole association model. This model
# is central to permission management, admin configuration, and system security.

# ---------------------------------------------------------------------------
# Role Model
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    # Unique identifier for the role
    id = Column(Integer, primary_key=True, index=True)

    # Name of the role (e.g., "admin", "technician", "manager")
    name = Column(String, unique=True, nullable=False)

    # Optional description of what the role represents or controls
    description = Column(String, nullable=True)

    # Relationship to UserRole association entries
    users = relationship("UserRole", back_populates="role")
