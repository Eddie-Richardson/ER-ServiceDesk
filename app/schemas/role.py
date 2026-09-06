# ER-ServiceDesk/app/schemas/role.py
"""
Request/response schemas for an authorization grouping assigned to
users.
"""

from pydantic import BaseModel, ConfigDict
from typing import List
from app.schemas.role_permission import RolePermission

class RoleBase(BaseModel):
    """Shared fields for Role across create/read/update."""
    name: str
    description: str | None = None

class RoleCreate(RoleBase):
    """Schema for creating a new Role record (client -> server)."""
    pass

class RoleUpdate(BaseModel):
    """Schema for partially updating an existing Role record. All fields optional."""
    name: str | None = None
    description: str | None = None

class Role(RoleBase):
    """Schema returned to the client for a Role record (server -> client)."""
    id: int
    role_permissions: List[RolePermission] = []
    model_config = ConfigDict(from_attributes=True)
