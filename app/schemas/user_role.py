# ER-ServiceDesk/app/schemas/user_role.py
# Pydantic schemas for UserRole entities
"""
Request/response schemas for the many-to-many link between users and
roles.
"""

from pydantic import BaseModel, ConfigDict

class UserRoleBase(BaseModel):
    """Shared fields for UserRole across create/read/update."""
    user_id: int
    role_id: int

class UserRoleCreate(UserRoleBase):
    """Schema for creating a new UserRole record (client -> server)."""
    pass

class UserRoleUpdate(BaseModel):
    """Schema for partially updating an existing UserRole record. All fields optional."""
    user_id: int | None = None
    role_id: int | None = None

class UserRole(UserRoleBase):
    """Schema returned to the client for a UserRole record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
