# ER-ServiceDesk/app/models/user_role.py
# UserRole association model linking users to roles
#
# Represents the many‑to‑many relationship between users and roles within the
# ER‑ServiceDesk RBAC (Role-Based Access Control) system. Each record connects
# a single user to a single role, defining the permissions available to that
# user through their assigned roles. This model is central to authorization
# logic and is used throughout authentication, permission checks, and admin
# management workflows.

# ---------------------------------------------------------------------------
# UserRole Model
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    # Unique identifier for the user-role association
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking to the user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Foreign key linking to the role
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # Relationship back to the User model
    user = relationship("User")

    # Relationship back to the Role model
    role = relationship("Role")
