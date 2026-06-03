# ER-ServiceDesk/app/models/permission.py
# Permission model for defining system access capabilities
#
# Represents a permission within the ER‑ServiceDesk authorization system.
# Permissions define specific capabilities or actions that users or roles
# may be granted. This model is used by the RBAC (Role-Based Access Control)
# system to determine what operations are allowed within the application.
# Permissions are typically assigned to roles, which are then assigned to users.

# ---------------------------------------------------------------------------
# Permission Model
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    # Unique identifier for the permission
    id = Column(Integer, primary_key=True, index=True)

    # Name of the permission (e.g., "create_ticket", "view_reports")
    name = Column(String, unique=True, nullable=False)

    # Optional human-readable description of what the permission allows
    description = Column(String, nullable=True)
