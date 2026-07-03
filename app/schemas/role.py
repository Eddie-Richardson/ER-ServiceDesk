# ER-ServiceDesk/app/schemas/role.py
# Pydantic schemas for Role entities used to validate and structure an authorization grouping assigned to users
"""
Pydantic schemas for Role entities used to validate and structure an authorization grouping assigned to users.
"""

from pydantic import BaseModel
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
    class Config:
        orm_mode = True
